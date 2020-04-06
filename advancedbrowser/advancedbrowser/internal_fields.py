# -*- coding: utf-8 -*-
# See github page to report issues or to contribute:
# https://github.com/hssm/advanced-browser
from anki.lang import _
from anki.cards import Card
from anki.lang import _
from anki.utils import intTime, splitFields
from aqt.utils import askUser, showWarning

from anki.consts import *



class InternalFields:

    def __init__(self):
        self.noteColumns = []
        self.cardColumns = []

    def onBuildContextMenu(self, contextMenu):
        nGroup = contextMenu.newSubMenu("- Note (internal) -")
        cGroup = contextMenu.newSubMenu("- Card (internal) -")

        for cc in self.noteColumns:
            nGroup.addItem(cc)
        for cc in self.cardColumns:
            cGroup.addItem(cc)

    def onAdvBrowserLoad(self, advBrowser):
        """Called when the Advanced Browser add-on has finished
        loading. Create and add all custom columns owned by this
        add-on here.

        """

        # Clear existing state
        self.noteColumns = []
        self.cardColumns = []

        def setData(c: Card, value: str):
            try:
                value = int(value)
            except ValueError:
                return False
            if not askUser(_("Do you really want to change the id of the note ? This may create problems during synchronisation if the note has been modified on another computer.")):
                return False
            old_nid = c.nid
            n = c.note()
            cards = n.cards()
            n.id = value
            n.flush()
            for card in cards:
                card.nid = value
                card.flush()
            c.col._remNotes([old_nid])
            return True

        cc = advBrowser.newCustomColumn(
            type="nid",
            name="Note ID",
            onData=lambda c, n, t: n.id,
            onSort=lambda: "n.id",
            setData=setData,
        )
        self.noteColumns.append(cc)

        def setData(c: Card, value: str):
            if not askUser(_("Do you really want to change the globally unique id of the note ? This may create problems during synchronisation if the note has been modified on another computer.")):
                return False
            n = c.note()
            n.guid = value
            n.flush(mod=intTime())
            return True

        cc = advBrowser.newCustomColumn(
            type="nguid",
            name="Note Guid",
            onData=lambda c, n, t: n.guid,
            onSort=lambda: "n.guid",
            setData=setData,
        )
        self.noteColumns.append(cc)

        cc = advBrowser.newCustomColumn(
            type="nmid",
            name="Model ID",
            onData=lambda c, n, t: n.mid,
            onSort=lambda: "n.mid"
        )
        self.noteColumns.append(cc)

        def setData(c: Card, value: str):
            try:
                value = int(value)
            except ValueError:
                return False
            c.col.db.execute("update cards set usn=? where id=?", value, c.id)
            
        cc = advBrowser.newCustomColumn(
            type="nusn",
            name="Note USN",
            onData=lambda c, n, t: n.usn,
            onSort=lambda: "n.usn",
            setData=setData,
        )
        self.noteColumns.append(cc)

        def setData(c: Card, value: str):
            n = c.note()
            fields = value.split(u"\u25A0")
            if len(fields) != len(n.fields):
                return False
            n.fields = fields
            n.flush()
            advBrowser.editor.loadNote()
            return True

        cc = advBrowser.newCustomColumn(
            type="nfields",
            name="Note Fields",
            onData=lambda c, n, t: u"\u25A0".join(n.fields),
            onSort=lambda: "n.flds",
            setData=setData,
        )
        self.noteColumns.append(cc)

        cc = advBrowser.newCustomColumn(
            type="nflags",
            name="Note Flags",
            onData=lambda c, n, t: n.flags,
            onSort=lambda: "n.flags"
        )
        self.noteColumns.append(cc)

        cc = advBrowser.newCustomColumn(
            type="ndata",
            name="Note Data",
            onData=lambda c, n, t: n.data,
            onSort=lambda: "n.data"
        )
        self.noteColumns.append(cc)

        def setData(c: Card, value: str):
            try:
                value = int(value)
            except ValueError:
                return False
            if not askUser(_("Do you really want to change the id of the card ? This may create problems during synchronisation if the note has been modified on another computer.")):
                return False
            old_cid = c.id
            c.id = value
            c.flush()
            c.col.remCards([old_cid], notes=False)
            c.col.db.execute(
                "update revlog set cid = ?, usn=? where cid = ?", value, c.col.usn(), old_cid)
            return True

        cc = advBrowser.newCustomColumn(
            type="cid",
            name="Card ID",
            onData=lambda c, n, t: c.id,
            onSort=lambda: "c.id",
            setData=setData,
        )
        self.cardColumns.append(cc)

        def setData(c: Card, value: str):
            new_deck = c.col.decks.get(value, default=False)
            if new_deck is None:
                return False
            old_deck = c.col.decks.get(c.did)
            if new_deck["dyn"] == DECK_DYN and old_deck["dyn"] == DECK_STD:
                # ensuring that if the deck is dynamic, then a
                # standard odid is set
                c.col.sched._moveToDyn(new_deck["id"], [c.id])
            else:
                c.did = new_deck["id"]
                if new_deck["dyn"] == DECK_STD and old_deck["dyn"] == DECK_DYN:
                    # code similar to sched.emptyDyn
                    if c.type == CARD_TYPE_LRN:
                        c.queue = QUEUE_TYPE_NEW
                        c.type = CARD_TYPE_NEW
                    else:
                        c.queue = c.type
                    c.due = c.odue
                    c.odue = 0
                    c.odid = 0
                c.flush()
            return True

        cc = advBrowser.newCustomColumn(
            type="cdid",
            name="Deck ID",
            onData=lambda c, n, t: c.did,
            onSort=lambda: "c.did",
            setData=setData,
        )
        self.cardColumns.append(cc)

        def setData(c: Card, value: str):
            if not c.odid:
                # only accept to change odid if there is already one
                return False
            deck = c.col.decks.get(value, default=False)
            if deck is None:
                return False
            if deck["dyn"] == DECK_DYN:
                return False
            c.flush()
            return True

        cc = advBrowser.newCustomColumn(
            type="codid",
            name="Original Deck ID",
            onData=lambda c, n, t: c.odid,
            onSort=lambda: "c.odid",
            setData=setData,
        )
        self.cardColumns.append(cc)

        def setData(c: Card, value: str):
            try:
                value = int(value)
            except ValueError:
                return False
            n = c.note()
            m = n.model()
            if value < 0:
                return False
            if m["type"] == MODEL_STD and value >= len(m["tmpls"]):
                # only accept values of actual template
                return False
            if not askUser(_("Do you really want to change the ord of the card ? The card may be empty, or duplicate, unless you know exactly what you do.")):
                return False
            c.ord = value
            return True

        cc = advBrowser.newCustomColumn(
            type="cord",
            name="Card Ordinal",
            onData=lambda c, n, t: c.ord,
            onSort=lambda: "c.ord",
            setData=setData,
        )
        self.cardColumns.append(cc)

        def setData(c: Card, value: str):
            try:
                value = int(value)
            except ValueError:
                return False
            c.col.db.execute("update cards set usn=? where id=?", value, c.id)

        cc = advBrowser.newCustomColumn(
            type="cusn",
            name="Card USN",
            onData=lambda c, n, t: c.usn,
            onSort=lambda: "c.usn",
            setData=setData,
        )
        self.cardColumns.append(cc)

        def setData(c: Card, value: str):
            try:
                value = int(value)
                if not 0 <= value <= 3:
                    return False
            except ValueError:
                value = {"new": 0, "lrn": 1, "rev": 2,
                         "relearning": 3}.get(value.strip().lower())
                if value is None:
                    return False
            if not askUser(_("Do you really want to change the card type of the card ? Values may be inconsistents if you don't change the queue type, due value, etc....")):
                return False
            c.type = value
            c.flush()
            return True

        cc = advBrowser.newCustomColumn(
            type="ctype",
            name="Card Type",
            onSort=lambda: "c.type",
            onData=lambda c, n, t: {
                0: _("New"),
                1: _("Lrn"),
                2: _("Rev"),
                3: _("Relearning"),
            }.get(c.type, c.type),
        )
        self.cardColumns.append(cc)

        def setData(c: Card, value: str):
            try:
                value = int(value)
                if not -3 <= value <= 4:
                    # 4 should not occur with V1
                    return False
            except ValueError:
                value = {"manually buried": -3, "sibling buried": -2, "suspended": -1, "new": 0,
                         "lrn": 1, "rev": 2, "day learn relearn": 3, "preview": 4}.get(value.strip().lower())
                if value is None:
                    return False
            if not askUser(_("Do you really want to change the queue type of the card ? Values may be inconsistents if you don't change the card type, due value, etc....")):
                return False
            c.type = value
            c.flush()
            return True

        cc = advBrowser.newCustomColumn(
            type="cqueue",
            name="Card Queue",
            onData=lambda c, n, t: {
                -3: _("Manually buried"),
                -2: _("Sibling buried"),
                -1: _("Type suspended"),
                0: _("New"),
                1: _("Lrn"),
                2: _("Rev"),
                3: _("Day learn relearn"),
                4: _("Preview"),
            }.get(c.queue, c.queue),
            onSort=lambda: "c.queue",
            setData=setData,
        )
        self.cardColumns.append(cc)

        def setData(c: Card, value: str):
            try:
                value = int(value)
            except ValueError:
                return False
            c.left = value
            return True

        cc = advBrowser.newCustomColumn(
            type="cleft",
            name="Card Left",
            onData=lambda c, n, t: c.left,
            onSort=lambda: "c.left",
            setData=setData,
        )
        self.cardColumns.append(cc)

        def setData(c: Card, value: str):
            try:
                value = int(value)
            except ValueError:
                return False
            if not askUser(_("Do you really want to change the original due. If the card is not already in a filtered deck, or moved to one, it may creates unexpected effect.")):
                return False
            c.odue = value
            c.flush()
            return True

        cc = advBrowser.newCustomColumn(
            type="codue",
            name="Card Original Due",
            onData=lambda c, n, t: c.odue,
            onSort=lambda: "c.odue",
            setData=setData,
        )
        self.cardColumns.append(cc)

        def setData(c: Card, value: str):
            try:
                value = int(value)
            except ValueError:
                value = {"":0, "no":0,"red":1, "orange":2, "green":3, "blue":4}.get(value.strip().lower())
                if value is None:
                    return False
            if not 0 <= value <= 4:
                return False
            c.setUserFlag(value)
            return True

        cc = advBrowser.newCustomColumn(
            type="cflags",
            name="Card Flags",
            onData=lambda c, n, t: c.flags,
            onSort=lambda: "c.flags",
            setData=setData,
        )
        self.cardColumns.append(cc)


iff = InternalFields()