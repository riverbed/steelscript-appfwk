# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import math


class NiceScale:
    def __init__(self, minval, maxval, maxticks=10, forcezero=False,
                 zerothresh=0.2):
        self.minval = minval if minval else 0
        self.maxval = maxval if maxval else 0
        self.maxticks = maxticks
        self.zerothresh = zerothresh
        self.forcezero = forcezero
        self.calculate()

    def calculate(self):
        """ Calculate and update values for tick spacing and nice
            minimum and maximum data points on the axis.
        """

        if (self.forcezero or (self.minval > 0) and
                (self.maxval > 0) and
                ((float(self.maxval - self.minval) / self.maxval)
                    > self.zerothresh)):
            self.minval = 0

        vrange = self.maxval - self.minval
        if vrange == 0:
            self.tickspacing = 1
            self.nicemin = 0
            self.nicemax = 1
            self.numticks = 1
        else:
            valrange = self.nicenum(vrange, False)
            self.tickspacing = self.nicenum(float(valrange) /
                                            (self.maxticks - 1), True)
            self.nicemin = (math.floor(self.minval / self.tickspacing)
                            * self.tickspacing)
            self.nicemax = (math.ceil(self.maxval / self.tickspacing)
                            * self.tickspacing)
            self.numticks = 1 + round((self.nicemax - self.nicemin)
                                      / self.tickspacing)

    def nicenum(self, valrange, round):
        """Returns a "nice" number approximately equal to valrange.

        :param valrange: the data range
        :param bool round: if true, round; if false, take the ceiling.
        """

        if valrange == 0:
            return 0

        exponent = math.floor(math.log10(valrange))
        fraction = valrange / math.pow(10, exponent)

        if round:
            if fraction < 1.5:
                nicefraction = 1
            elif fraction < 3:
                nicefraction = 2
            elif fraction < 7:
                nicefraction = 5
            else:
                nicefraction = 10
        else:
            if fraction <= 1:
                nicefraction = 1
            elif fraction <= 2:
                nicefraction = 2
            elif fraction <= 5:
                nicefraction = 5
            else:
                nicefraction = 10

        return nicefraction * math.pow(10, exponent)

    def dump(self):
        vals = []
        val = self.nicemin
        while val <= self.nicemax:
            vals.append("{0:.4f}".format(val))
            val += self.tickspacing

        print "(%.4f - %.4f @ %d) => %d [%s]" % (self.minval,
                                                 self.maxval,
                                                 self.maxticks,
                                                 self.numticks,
                                                 ', '.join(vals))

if __name__ == "__main__":
    def test(minval, maxval, maxticks=10):
        n = NiceScale(minval, maxval, maxticks)
        n.dump()

    #test(100,500)
    #test(100,500,5)
    #test(100,500,4)
    #test(92,156)
    #test(0.09,.9)
    #test(0.2, 0.28)
    #test(1, 19)
    test(0.101, 0.119)