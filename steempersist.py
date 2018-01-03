#!/usr/bin/python3
import steem
import json
import dateutil.parser
import datetime
import time
import syslog
import hashlib
p = None

#Helper class for keeping some state synced to a JSON file all the time. This should allow the bot
#to always pick up things without loss of transactions even if the python process bails out
#completely.
class Progress:
    def __init__(self, pbs, pname):
        self.filename = pname + ".json"
        try:
            #Read from the old JSON file if it exists.
            syslog.syslog("Fetching old state from JSON backup")
            with open(self.filename) as pjson:
                self.state = json.loads(pjson.read())
        except:
            #If it doesn't start off with a clean slate.
            syslog.syslog("No backup, setting up starting point")
            self.state = dict()
            self.state["block_no"] = pbs.get_current_block_num() - 140
            self.state["trx_no"] = 0
            self.state["op_no"] = 0
            self.state["rtime"] = time.time()
        syslog.syslog("New start, block " + str(self.state["block_no"]) + " tx " + \
                      str(self.state["trx_no"]) + " op " + str(self.state["op_no"]))
    #An other operation processed without exceptions.
    def __call__(self, pblock, trx, opp, flush=False):
        #Remember previous block number for a sec.
        oldblock = self.state["block_no"]
        #Update block, trx  and operation numbers
        self.state["block_no"] = pblock
        self.state["trx_no"] = trx
        self.state["op_no"] = opp
        #Write as JSON to file system if explicitly requested or every 100th block.
        if flush or (oldblock != pblock and (pblock % 100) == 0):
            with open(self.filename, "w") as pjson:
                pjson.write(json.dumps(self.state))
            return True
        return False
    #Sync explicitly, to be used after real activity to avoid double processing of operations.
    def sync(self):
        with open(self.filename, "w") as pjson:
            pjson.write(json.dumps(self.state))

#Generator function, NOTE: name no longer describes what it yields
def stream_blockchain_events(sbs,handled,pname):
    global p
    unhandled = set()
    #Run as long as we get 'expected' exceptions from BlockChain::stream_from main loop.
    while True:
        try:
            #Start of with a new JSON state sync object.
            p = Progress(sbs,pname)
            skipfirst = p.state["trx_no"]
            first = True
            block_no = -1
            trx_no = -1
            op_no = -1
            #A main loop that throws exceptions on a regular basis.
            #Start at the last block from the previous time this loop was run.
            for entry in sbs.stream_from(p.state["block_no"]):
                block_no = entry["block"]
                trx_no = entry["trx_in_block"]
                op_no = entry["op_in_trx"]
                lop = entry["op"]
                if first is False and trx_no == 0 and op_no == 0:
                    skipfirst = -1
                first = False
                event_time = dateutil.parser.parse(entry["timestamp"])
                #Skip already processed transactions from block if needed.
                if skipfirst >= trx_no:
                    pass
                else:
                    sync = False
                    if lop[0] in handled:
                        yield [lop[0], event_time, lop[1]]
                        sync = True
                    else:
                        if not lop[0] in unhandled:
                            unhandled.add(lop[0])
                            syslog.syslog("Unhandled event type: " + lop[0])
                        if "other" in handled:
                            yield ["other",event_time, {"type" : lop[0], "event" : lop[1]}]
                    #Inform the Progress object of our latest progress.
                    if p(block_no, trx_no, op_no, sync):
                        #If our progress resulted in an explicit or implicit SYNC,
                        #do some extra stuff.
                        #Log how far are we behind on the HEAD of the blockchain?
                        behind = datetime.datetime.utcnow() - \
                                 dateutil.parser.parse(entry["timestamp"])
                        if op_no == 0 and trx_no == 0:
                            syslog.syslog("[block " + str(block_no) + " tx " + \
                                      str(trx_no) + "op" + str(op_no) +"] behind " + \
                                      str(behind))
                now = time.time()
                if "hour" in handled:
                    if (now - p.state["rtime"]) >= 3600:
                        # one hour (or more) passed.
                        p.state["rtime"] = now
                        yield ["hour", event_time, {}]
                        p.sync()
                else:
                    if "day" in handled:
                        if (now - p.state["rtime"]) >= 86400:
                            # one day (or more) passed.
                            p.state["rtime"] = now
                            yield ["day", event_time, {}]
                            p.sync()

        #Some expected exceptions from Blockchain::stream_from
        except TypeError as e:
            syslog.syslog("ERR " + str(e) + " " + str(block_no) + " " + str(trx_no))
            p.sync()
        except AttributeError as e:
            syslog.syslog("ERR " + str(e) + " " + str(block_no) + " " + str(trx_no))
            p.sync()
#        except Exception as e:
#            syslog.syslog("ERR " + str(e))

class PersistentDict:
    def __init__(self,name):
        self.name = name
    def __getitem__(self,key):
        global p
        if key in p.state[self.name]:
            return p.state[self.name][key]
        else:
            return None
    def __setitem__(self,key,val):
        global p
        p.state[self.name][key] = val
    def clear(self):
        p.state[self.name] = dict()

class SteemPersist:
    def __init__(self,name):
        self.name=name
        syslog.openlog(name,syslog.LOG_PID)
        syslog.syslog("START")
        self.steemd = steem.steemd.Steemd()
        self.blockchain = steem.blockchain.Blockchain(self.steemd)
        self.handlers = dict()
        self.handled = set()
    def __getitem__(self,name):
        global p
        full_name = "cd_" + name
        if not full_name in p.state:
            p.state[full_name] = dict()
        return PersistentDict(full_name)
    def sync(self):
        global p
        p.sync()
    def set_handler(self,event,handler):
        self.handlers[event] = handler
        self.handled.add(event)
    def set_handlers(self,obj):
        for key in dir(obj):
            if key[0] != "_":
                self.set_handler(key,getattr(obj,key))
    def __call__(self):
        if len(self.handled) > 0:
            for r in stream_blockchain_events(self.blockchain,self.handled,self.name):
                self.handlers[r[0]](r[1],r[2])

