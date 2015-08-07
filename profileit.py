# -*- coding: utf-8 -*-
import sys
import os
import re
import hotshot
import hotshot.stats
import tempfile
import StringIO
import functools

words_re = re.compile(r'\s+')

group_prefix_re = [
    re.compile("^(.*)/[^/]+$"),  # extract module path
    re.compile(".*"),            # catch strange entries
]


class Profilling(object):

    def __init__(self, log=None):
        self.log = log
        self.tmpfile = tempfile.mktemp()
        self.prof = hotshot.Profile(self.tmpfile)

    def run(self, func, *callback_args, **callback_kwargs):
        return self.prof.runcall(func, *callback_args, **callback_kwargs)

    def get_group(self, file):
        for g in group_prefix_re:
            name = g.findall(file)
            if name:
                return name[0]

    def get_summary(self, results_dict, sum):
        list = [(item[1], item[0]) for item in results_dict.items()]
        list.sort(reverse=True)
        list = list[:40]

        res = "      tottime\n"
        for item in list:
            res += "%4.1f%% %7.3f %s\n" % (100*item[0]/sum if sum else 0, item[0], item[1])

        return res

    def summary_for_files(self, stats_str):
        stats_str = stats_str.split("\n")[5:]

        mystats = {}
        mygroups = {}

        sum = 0

        for s in stats_str:
            fields = words_re.split(s)
            if len(fields) == 7:
                time = float(fields[2])
                sum += time
                file = fields[6].split(":")[0]

                if file not in mystats:
                    mystats[file] = 0
                mystats[file] += time

                group = self.get_group(file)
                if group not in mygroups:
                    mygroups[group] = 0
                mygroups[group] += time

        return " ---- By file ----\n\n" + self.get_summary(mystats, sum) + "\n" + \
               " ---- By group ---\n\n" + self.get_summary(mygroups, sum)

    def get_result(self):
        self.prof.close()

        out = StringIO.StringIO()
        old_stdout = sys.stdout
        sys.stdout = out

        stats = hotshot.stats.load(self.tmpfile)
        stats.sort_stats('time', 'calls')
        stats.print_stats()

        sys.stdout = old_stdout
        stats_str = out.getvalue()

        if stats_str:
            content = "\n\n" + stats_str + "\n\n"

        content = "\n".join(content.split("\n")[:40])

        content += self.summary_for_files(stats_str)

        os.unlink(self.tmpfile)

        if self.log:
            f = file(self.log, "a")
            f.write(content)
            f.close()
        else:
            print content


def profileit_base(log):
    def _profileit(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            p = Profilling(log)
            p.run(func, *args, **kwargs)
            p.get_result()
        return wrapper
    return _profileit


def profileit(funshion=None, log=None):
    actual_decorator = profileit_base(log)
    if funshion:
        return actual_decorator(funshion)
    else:
        return actual_decorator


if __name__ == "__main__":
    import time

    @profileit(log="a")
    def test(a, b, c):
        time.sleep(1)
        print a, b, c

    test(1, 2, 3)

    class A(object):

        @profileit
        def x(self, a):
            time.sleep(0.5)
            print a

    a = A()
    a.x(1)
