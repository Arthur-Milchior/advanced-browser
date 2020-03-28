# -*- coding: utf-8 -*-
# See github page to report issues or to contribute:
# https://github.com/hssm/advanced-browser

import time

from anki.hooks import addHook, wrap
from anki.rsbackend import FormatTimeSpanContext
from aqt import *


class CustomFields:

    def onAdvBrowserLoad(self, advBrowser):
        """Called when the Advanced Browser add-on has finished
        loading. Create and add all custom columns owned by this
        module."""

        # Store a list of CustomColumns managed by this module. We later
        # use this to build our part of the context menu.
        self.customColumns = []

        # Convenience method to create lambdas without scope clobbering
        def getOnSort(f): return lambda: f

        # -- Columns -- #

        # First review

        def cFirstOnData(c, n, t):
            first = mw.col.db.scalar(
                "select min(id) from revlog where cid = ?", c.id)
            if first:
                return time.strftime("%Y-%m-%d", time.localtime(first / 1000))

        cc = advBrowser.newCustomColumn(
            type='cfirst',
            name='First Review',
            onData=cFirstOnData,
            onSort=lambda: "(select min(id) from revlog where cid = c.id)"
        )
        self.customColumns.append(cc)

        # Last review
        def cLastOnData(c, n, t):
            last = mw.col.db.scalar(
                "select max(id) from revlog where cid = ?", c.id)
            if last:
                return time.strftime("%Y-%m-%d", time.localtime(last / 1000))

        cc = advBrowser.newCustomColumn(
            type='clast',
            name='Last Review',
            onData=cLastOnData,
            onSort=lambda: "(select max(id) from revlog where cid = c.id)"
        )
        self.customColumns.append(cc)

        # Average time
        def cAvgtimeOnData(c, n, t):
            avgtime = mw.col.db.scalar(
                "select avg(time)/1000.0 from revlog where cid = ?", c.id)
            return mw.col.backend.format_time_span(avgtime)

        cc = advBrowser.newCustomColumn(
            type='cavgtime',
            name='Time (Average)',
            onData=cAvgtimeOnData,
            onSort=lambda: "(select avg(time) from revlog where cid = c.id)"
        )
        self.customColumns.append(cc)

        # Total time
        def cTottimeOnData(c, n, t):
            tottime = mw.col.db.scalar(
                "select sum(time)/1000.0 from revlog where cid = ?", c.id)
            return mw.col.backend.format_time_span(tottime)

        cc = advBrowser.newCustomColumn(
            type='ctottime',
            name='Time (Total)',
            onData=cTottimeOnData,
            onSort=lambda: "(select sum(time) from revlog where cid = c.id)"
        )
        self.customColumns.append(cc)

        # Fastest time
        def cFasttimeOnData(c, n, t):
            tm = mw.col.db.scalar(
                "select time/1000.0 from revlog where cid = ? "
                "order by time asc limit 1", c.id)
            return mw.col.backend.format_time_span(tm)

        srt = ("(select time/1000.0 from revlog where cid = c.id "
               "order by time asc limit 1)")

        cc = advBrowser.newCustomColumn(
            type='cfasttime',
            name='Fastest Review',
            onData=cFasttimeOnData,
            onSort=getOnSort(srt)
        )
        self.customColumns.append(cc)

        # Slowest time
        def cSlowtimeOnData(c, n, t):
            tm = mw.col.db.scalar(
                "select time/1000.0 from revlog where cid = ? "
                "order by time desc limit 1", c.id)
            return mw.col.backend.format_time_span(tm)

        srt = ("(select time/1000.0 from revlog where cid = c.id "
               "order by time desc limit 1)")

        cc = advBrowser.newCustomColumn(
            type='cslowtime',
            name='Slowest Review',
            onData=cSlowtimeOnData,
            onSort=getOnSort(srt)
        )
        self.customColumns.append(cc)

        # Overdue interval
        def cOverdueIvl(c, n, t):
            val = self.valueForOverdue(c.odid, c.queue, c.type, c.due)
            if val:
                return mw.col.backend.format_time_span(val, context=FormatTimeSpanContext.INTERVALS)

        # fixme: this will need to be converted into an sql case statement
        srt = (f"""
        select
          (case
             when odid then null
             when queue = {QUEUE_TYPE_LRN} then null
             when queue = {QUEUE_TYPE_NEW} then null
             when type = {CARD_TYPE_NEW} then null
             when {mw.col.sched.today} - due <= 0 then null
             when (queue = {QUEUE_TYPE_REV} or queue = {QUEUE_TYPE_DAY_LEARN_RELEARN} or (type = {CARD_TYPE_REV} and queue < 0)) then ({mw.col.sched.today} - due)
          )
        where id = c.id""")

        cc = advBrowser.newCustomColumn(
            type='coverdueivl',
            name="Overdue Interval",
            onData=cOverdueIvl,
            onSort=getOnSort(srt)
        )
        self.customColumns.append(cc)

        # Previous interval
        def cPrevIvl(c, n, t):
            ivl = mw.col.db.scalar(
                "select ivl from revlog where cid = ? "
                "order by id desc limit 1 offset 1", c.id)
            if ivl is None:
                return
            elif ivl == 0:
                return "0 days"
            elif ivl > 0:
                return mw.col.backend.format_time_span(ivl*86400, context=FormatTimeSpanContext.INTERVALS)
            else:
                return mw.col.backend.format_time_span(-ivl, context=FormatTimeSpanContext.INTERVALS)

        srt = ("(select ivl from revlog where cid = c.id "
               "order by id desc limit 1 offset 1)")

        cc = advBrowser.newCustomColumn(
            type='cprevivl',
            name="Previous Interval",
            onData=cPrevIvl,
            onSort=getOnSort(srt)
        )
        self.customColumns.append(cc)

        # Percent correct
        def cPctCorrect(c, n, t):
            if c.reps > 0:
                return "{:2.0f}%".format(
                    100 - ((c.lapses / float(c.reps)) * 100))
            return "0%"

        cc = advBrowser.newCustomColumn(
            type='cpct',
            name='Percent Correct',
            onData=cPctCorrect,
            onSort=lambda: "cast(c.lapses as real)/c.reps"
        )
        self.customColumns.append(cc)

        # Previous duration
        def cPrevDur(c, n, t):
            time = mw.col.db.scalar(
                "select time/1000.0 from revlog where cid = ? "
                "order by id desc limit 1", c.id)
            return mw.col.backend.format_time_span(time)

        srt = ("(select time/1000.0 from revlog where cid = c.id "
               "order by id desc limit 1)")

        cc = advBrowser.newCustomColumn(
            type='cprevdur',
            name="Previous Duration",
            onData=cPrevDur,
            onSort=getOnSort(srt)
        )
        self.customColumns.append(cc)

        # Date (and time) created
        def cDateTimeCrt(c, n, t):
            return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(c.note().id/1000))

        cc = advBrowser.newCustomColumn(
            type='cdatetimecrt',
            name='Created (full)',
            onData=cDateTimeCrt,
            onSort=lambda: "n.id"
        )
        self.customColumns.append(cc)

        # fixme: sorting
        cc = advBrowser.newCustomColumn(
            type="cdeck",
            name="Current Deck (filtered)",
            onData=lambda c, n, t: advBrowser.mw.col.decks.name(c.did),
            onSort=lambda: "c.did"  # "nameForDeck(c.did)",
        )
        self.customColumns.append(cc)

    def onBuildContextMenu(self, contextMenu):
        """Build our part of the browser columns context menu."""

        group = contextMenu.newSubMenu("- Advanced -")
        for column in self.customColumns:
            group.addItem(column)

    def valueForOverdue(self, odid, queue, type, due):
        if odid or queue == QUEUE_TYPE_LRN:
            return
        elif queue == QUEUE_TYPE_NEW or type == CARD_TYPE_NEW:
            return
        else:
            diff = mw.col.sched.today - due
            if diff <= 0:
                return
            if queue in (QUEUE_TYPE_REV, QUEUE_TYPE_DAY_LEARN_RELEARN) or (type == CARD_TYPE_REV and queue < 0):
                return diff
            else:
                return


cf = CustomFields()
addHook("advBrowserLoaded", cf.onAdvBrowserLoad)
addHook("advBrowserBuildContext", cf.onBuildContextMenu)