""" 
    Record hashes of a number of named objects 
    is effectively triggered if any of them change state

    the name is what identifies the object. 
"""
import hashlib
import json


class FrozenStateModificationException(Exception):
    pass

class StateWatcher:
    def __init__(self, state_name: str, frozen: bool = False):

        self.states = {}
        self.name = state_name
        self.running_hash = hashlib.new('sha256')
        self.total_hash = int(self.running_hash.hexdigest(), 16)
        self.triggered = False
        self.frozen = frozen


    def add(self, name: str, value):
        if self.frozen:
            raise FrozenStateModificationException
        value_hash = bytes(hash(value))
        self.running_hash.update(value_hash)
        self.total_hash = int(self.running_hash.hexdigest(), 16)
        self.states[name] = value_hash

    def __hash__(self):
        return int(self.total_hash.hexdigest(), 16)

    def __eq__(self, other):
        return self.total_hash == other.total_hash

    def save(self, filename: str):
        """ Save the object to json"""
        with open(filename, "w+", encoding = "utf-8") as statef:
            data = {
                    "name": self.name, 
                    "total_hash": self.total_hash, 
                    "states" : self.states 
            }
            json.dump(data, statef, indent=4)

    @classmethod
    def load(cls, filename: str):
        """factory to make an instance from a file but this cannot be updated becasue of the 
           way hashlib works"""
        with open(filename, "r", "utf-8") as jf:
            data = json.load(jf)
            st = cls(data["name"], frozen = True)
            st.states = data["states"]
            st.total_hash = data["total_hash"]
        return st



