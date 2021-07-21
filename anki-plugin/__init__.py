# import the main window object (mw) from ankiqt
from aqt import mw
# import the "show info" tool from utils.py
# from aqt.utils import showInfo
import aqt.utils
# import all of the Qt GUI library
from aqt.qt import *

import io, json, os, subprocess

from . import util
'''this is an AnkiConnect file'''

EXAMPLE_SYNC_TARGET = 'username@example.com:/path/to/anki-data'
SYNC_CMD = ['rsync', '-rcz', '--stats']

def shellquote(s):
    return "'" + s.replace("'", "'\\''") + "'"

def getPaths():
    db_path = os.path.dirname(mw.col.path)
    json_filename = os.path.join(db_path, 'anki-slideshow.json')
    media_path = os.path.join(db_path, 'collection.media')
    return json_filename, media_path

def getPrevData():
    json_filename, media_path = getPaths()
    try:
        f = open(json_filename, 'r', encoding='utf-8')
        prev_data = json.load(f)
    except:
        prev_data = {}
    return prev_data

def exportCardsToWeb():
    json_filename, media_path = getPaths()
    export = {
        "decks": {},
        "cards": {}
    }
    
    for deck in mw.col.decks.all():
        deckName = deck['name']
        if deckName == 'Custom Study Session': continue
        #changed findCards to find_cards
        '''how to make card ID's show up in the deck field??????'''
        export["decks"][deckName] = [int(cid) for cid in mw.col.find_cards("deck:'%s'" % deckName)]
        
        #moved iterating up here to have program iterate through all decks
        # New method to iterate over cards
        for cid in mw.col.find_cards(f"deck:{deckName}"):
            card = mw.col.getCard(cid)
            tags = mw.col.getNote(card.nid).tags
            # for tag in tags:
            #     card["lec"] = tag

            '''from AnkiConnect cardsInfo method'''
            result = []
            model = card.model()
            note = card.note()
            fields = {}
            for info in model['flds']:
                order = info['ord']
                name = info['name']
                fields[name] = {'value': note.fields[order], 'order': order}

            result.append({
                'cardId': card.id,
                'fields': fields,
                'fieldOrder': card.ord,
                'question': util.cardQuestion(card),
                'answer': util.cardAnswer(card),
                'modelName': model['name'],
                'ord': card.ord,
                'deckName': deckName,
                'css': model['css'],
                'factor': card.factor,
                #This factor is 10 times the ease percentage,
                # so an ease of 310% would be reported as 3100
                'interval': card.ivl,
                'note': card.nid,
                'type': card.type,
                'queue': card.queue,
                'due': card.due,
                'reps': card.reps,
                'lapses': card.lapses,
                'left': card.left,
            })
            '''from AnkiConnect cardsInfo method'''

            export["cards"][cid] = result
    '''for card in mw.col.renderQA(None, "all"):
        id = card["id"]
        del card["id"]
        tags = mw.col.getNote(mw.col.getCard(id).nid).tags
        for tag in tags:
            if tag[0:11] == "zz_lecture_":
                card["lec"] = int(tag[11:])
        export["cards"][id] = card
    '''

    # If there is no sync target saved in the previous configuration, ask for it
    prev_data = getPrevData()
    while prev_data.get('sync_target', None) == None:
        prev_data = getSyncTarget(prev_data)
        
    export['sync_target'] = prev_data['sync_target']
        
    with open(json_filename, 'w', encoding='utf-8') as f:
        # f.write(json.dumps(export, ensure_ascii=False))
        json.dump(export, f, ensure_ascii=False)
    
    # err = None
    if export['sync_target'] != '':
        try:
            args = SYNC_CMD + [json_filename, media_path, export['sync_target']]
            out = subprocess.check_output(' '.join(map(shellquote, args)), stderr=subprocess.STDOUT, shell=True)
            aqt.utils.showInfo("Cards exported: %d\n\nSync results:\n%s" % (len(export["cards"]), out))
        except subprocess.CalledProcessError as err:
            aqt.utils.showInfo("Sync command failed with code %d. Here's the output:\n%s" % (err.returncode, err.output))
            pass
    
    # # Show the results of what we've done
    # if err is not None:
    #     # The sync command returned with a nonzero code
    #     aqt.utils.showInfo("Sync command failed with code %d. Here's the output:\n%s" % (err.returncode, err.output))
    # else:
    #     # There were no errors.
    #     aqt.utils.showInfo("Cards exported: %d\n\nSync results:\n%s" % (len(export["cards"]), out))
        
def getSyncTarget(prev_data = None):
    json_filename, media_path = getPaths()
    
    label = '''You'll need to sync the files to the anki-data folder in the Rack application.
Enter the [[username@]hostname:]path to the anki-data folder (which can be on another server).
We'll try to use rsync to automatically copy them.  Ensure that you have permissions to rsync -r
to this destination, and if it is remote, set up SSH keys so that a password is not required.'''
    
    called_during_export = prev_data is not None
    if not called_during_export: prev_data = getPrevData()
    prev_target = prev_data.get('sync_target', False)
    if prev_target is False: prev_target = EXAMPLE_SYNC_TARGET
    if called_during_export:
        label += "\n\nIf you intend to move/symlink files into the anki-data folder manually, click Cancel."
    
    text, ok = QInputDialog.getText(mw, 'Set Sync Destination', label, QLineEdit.Normal, prev_target)
    
    if ok:
        prev_data['sync_target'] = text
    elif called_during_export:
        prev_data['sync_target'] = ''
    
    if called_during_export:
        return prev_data
    else:
        # The export will not write this to disk, we have to do it ourselves
        with io.open(json_filename, 'w', encoding='utf-8') as f:
            f.write(json.dumps(prev_data, ensure_ascii=False).encode("utf-8"))

# create new menu items for both of those functions and add them to the Tools menu
mw.form.menuTools.addSeparator()



# action = QAction("Export Cards to Anki-Slideshow", mw)
# mw.connect(action, SIGNAL("triggered()"), exportCardsToWeb)
# mw.form.menuTools.addAction(action)
exportCardsAction = QAction("Export Cards to Anki-Slideshow", mw)
mw.form.menuTools.addAction(exportCardsAction)
exportCardsAction.triggered.connect(exportCardsToWeb)
mw.form.menuTools.addAction(exportCardsAction)

# action = QAction("Change Sync Destination for Anki-Slideshow", mw)
# mw.connect(action, SIGNAL("triggered()"), getSyncTarget)
# mw.form.menuTools.addAction(action)
syncAction = QAction("Change Sync Destination for Anki-Slideshow", mw)
mw.form.menuTools.addAction(syncAction)
syncAction.triggered.connect(getSyncTarget)
mw.form.menuTools.addAction(syncAction)