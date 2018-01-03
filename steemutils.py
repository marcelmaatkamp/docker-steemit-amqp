#!/usr/bin/python3
import steem
import datetime
import dateutil
import dateutil.parser

#Don't let 100% voting power go to waste, use it. This function returns true if our voting power is higher than 99.85%
def must_vote(account,minvp):
    stm=steem.steemd.Steemd()
    acc = stm.get_account(account)
    vp = acc["voting_power"]
    lvt = acc["last_vote_time"]
    more_vp = int((datetime.datetime.utcnow() - dateutil.parser.parse(lvt)).total_seconds() / 43.2)
    full_vp = vp + more_vp
    if full_vp > minvp:
        return True
    return False


