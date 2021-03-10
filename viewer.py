from __future__ import print_function, unicode_literals

from pprint import pprint

import curses
import sys
import os
import time
import re
import random
import traceback
from enum import Enum

class Dir(Enum):
    UP = 1
    DOWN = 2
    LEFT = 3
    RIGHT = 4

class StraceObj:

    def __init__(self, file_path):
        assert os.path.exists(file_path)
        self.file_path = file_path
        self.pid_regex = '^([0-9]+)'
        self.lines = []
        self.pid_dict = {}
        self.instance = None
        self.max_line_len = 0
        with open(self.file_path, 'r') as f:
            file_len = len(f.readlines())
        self.instance = CursesStrace(file_len, self)
        self.parse_file()

    
    def parse_file(self):
        with open(self.file_path, 'r') as f:
            for i, line in enumerate(f):
                self.max_line_len = len(line) if self.max_line_len < len(line) else self.max_line_len
                pid = re.search(self.pid_regex, line).group(0)
                if pid not in self.pid_dict:
                    self.pid_dict[pid] = curses.color_pair(random.randint(2, 7))
                self.instance.add_new_line(line, color=self.pid_dict[pid])
                self.lines.append((line, self.pid_dict[pid]))

    def run(self):
        while True:
            c = self.instance.screen.getch()
            if c == curses.KEY_LEFT or c == ord('h'):
                self.instance.cursor_update(Dir.LEFT)
            elif c == curses.KEY_RIGHT or c == ord('l'):
                self.instance.cursor_update(Dir.RIGHT)
            elif c == curses.KEY_UP or c == ord('k'):
                self.instance.cursor_update(Dir.UP)
            elif c == curses.KEY_DOWN or c == ord('j'):
                #moved = self.instance.scroll(4)
                self.instance.cursor_update(Dir.DOWN)
            elif c == ord('q'):
                break

    def parse_line(self, line):
        pass

class CursesStrace:

    def __init__(self, file_len, straceobj):
        self.screen = curses.initscr()
        curses.cbreak()
        curses.noecho()
        curses.curs_set(2)
        self.screen.keypad(True)
        self.screen.refresh()
        self.init_colors()

        self.strace_obj = straceobj
        self.file_len = file_len
        self.height, self.width = self.screen.getmaxyx()
        self.main_window_line = 1
        self.width_bound = int(self.width*0.75)
        self.hscroll_pos = 0
        self.vscroll_pos = 0
        self.cursor_x, self.cursor_y = 1, 1
        self.max_hscroll = self.width_bound
        self.max_vscroll = self.height
        self.doc_pos = self.height - 1
        self.init_main_window()
        self.init_sidebar()
    
    def init_colors(self):
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_BLACK,-1)
        curses.init_pair(2, curses.COLOR_BLUE, -1)
        curses.init_pair(3, curses.COLOR_CYAN, -1)
        curses.init_pair(4, curses.COLOR_GREEN, -1)
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)
        curses.init_pair(6, curses.COLOR_RED, -1)
        curses.init_pair(7, curses.COLOR_YELLOW, -1)
        curses.init_pair(8, curses.COLOR_WHITE, -1)

    def cursor_update(self, dir):
        if dir == Dir.LEFT:
            if self.cursor_x > 0:
                self.cursor_x -= 1
                self.hscroll(Dir.LEFT)

        elif dir == Dir.RIGHT:
            if self.cursor_x < self.width_bound:
                self.cursor_x += 1
                self.hscroll(Dir.RIGHT)

        elif dir == Dir.UP:
            if self.cursor_y > 1:
                self.cursor_y -= 1
                self.vscroll(Dir.UP, *self.strace_obj.lines[self.doc_pos - self.height])

        elif dir == Dir.DOWN:
            if self.cursor_y < self.height:
                self.cursor_y += 1
                self.vscroll(Dir.DOWN, *self.strace_obj.lines[self.doc_pos])
        self.main_win.move(self.cursor_y, self.cursor_x)


    def hscroll(self, dir):
        if dir == Dir.LEFT:
            self.hscroll_pos -= 1
            self.hscroll_pos = 0 if self.hscroll_pos < 0 else self.hscroll_pos
        if dir == Dir.RIGHT:
            self.hscroll_pos += 1
            self.hscroll_pos = self.max_hscroll if self.hscroll_pos > self.max_hscroll else self.hscroll_pos
        
        self.main_win.border()
        self.main_win.refresh(0, self.hscroll_pos, 0, 0, self.height, self.width_bound)

    def init_main_window(self):
        self.main_win = curses.newpad(self.height, self.width+1000)
        self.main_win.border()
        self.main_win.refresh(0, self.hscroll_pos, 0, 0, self.height, self.width_bound)
    
    def add_new_line(self, line, color=0):
        line = line.strip()
        if self.main_window_line < self.height - 1:
            self.main_win.addstr(self.main_window_line, 2, line, color)
            self.main_win.border()
            self.main_win.refresh(0, self.hscroll_pos, 0, 0, self.height, self.width_bound)
            self.main_window_line += 1
            self.max_hscroll = len(line) if len(line) > self.max_hscroll else self.max_hscroll
    
    def vscroll(self, dir, replace_str, color):
        if dir == Dir.DOWN:
            self.main_window_line = self.height - 2 
            self.doc_pos += 1
            self.main_win.move(0, 0)
            self.main_win.deleteln()
            self.main_win.move(self.height-2, 0)
            self.main_win.clrtoeol()
            self.add_new_line(replace_str, color)

        elif dir == Dir.UP:
            self.main_window_line = 1
            self.doc_pos -= 1
            self.main_win.move(0, 0)
            self.main_win.clrtoeol()
            self.main_win.insertln()
            self.add_new_line(replace_str, color)

    def init_sidebar(self):
        pass

if __name__ == '__main__':
    if len(sys.argv) == 2:
        try:
            strace = StraceObj(sys.argv[1])
            strace.run()
        except KeyboardInterrupt:
            curses.endwin()
        except curses.error as e:
            curses.endwin()
            traceback.print_exc()
        curses.endwin()
