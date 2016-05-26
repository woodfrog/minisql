import unittest
import os
import time
from buffer_manager import Block, BufferManager


def prepare_file():
    with open('foo', 'wb') as file:
        file.write(b'Hello World')


class TestBlock(unittest.TestCase):
    def test_block(self):
        prepare_file()

        block = Block(5, 'foo', 0)
        self.assertEqual(block.read(), b'Hello')  # test read
        block.write(b'abcde')
        self.assertEqual(block.read(), b'abcde')  # test write
        self.assertTrue(block.dirty)  # test that write sets dirty bit
        block.flush()
        self.assertFalse(block.dirty)  # test that flush resets dirty bit
        with open('foo', 'rb') as f:
            self.assertEqual(f.read(), b'abcde World')  # test flush writes back to file
        block.pin()
        self.assertEqual(block.pin_count, 1)  # test
        with self.assertRaises(RuntimeError):
            block.release()
        block.unpin()
        self.assertEqual(block.pin_count, 0)  # test that release unpins the block
        block.release()
        self.assertTrue(block.file.closed)  # test that release doesn't close the file

    def test_partial_read(self):
        prepare_file()
        block = Block(5, 'foo', 2)  # test partial read
        self.assertEqual(block.effective_bytes, 1)
        self.assertEqual(block.read(), b'd')
        block.write(b'D')
        self.assertEqual(block.read(), b'D')
        block.release()
        with open('foo', 'rb') as file:
            self.assertEqual(file.read(), b'Hello WorlD')


class TestBufferManager(unittest.TestCase):
    def test_buffer_manager(self):
        BufferManager.block_size = 5
        BufferManager.total_blocks = 2
        prepare_file()
        manager = BufferManager()
        a = manager.get_file_block('foo', 0)
        a.pin()
        self.assertEqual(a.read(), b'Hello')
        b = manager.get_file_block('./foo', 0)
        self.assertTrue(a is b)  # test cache hit

        b = manager.get_file_block('foo', 1)
        b.pin()
        time.sleep(1)
        self.assertEqual(b.read(), b' Worl')
        with self.assertRaises(RuntimeError):
            c = manager.get_file_block('foo', 2)  # test buffer run out of space
        a.unpin()
        b.unpin()
        c = manager.get_file_block('foo', 2)  # test lru swap
        self.assertFalse((os.path.abspath('foo'), 0) in manager._blocks.keys())  # a should be swapped out
        self.assertTrue((os.path.abspath('foo'), 1) in manager._blocks.keys())  # b should remain in the buffer
        manager.free()


if __name__ == '__main__':
    unittest.main()
