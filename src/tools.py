import codecs

import pickle


class Tool:

    @classmethod
    def pickle(cls, obj):
        pickled = codecs.encode(pickle.dumps(obj), "base64").decode()
        return pickled

    @classmethod
    def unpickle(cls, text):
        unpickled = pickle.loads(codecs.decode(text.encode(), "base64"))
        return unpickled
