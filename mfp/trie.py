"""
very basic prefix tree implementation for command line completion

Copyright (c) Bill Griblbe <grib@billgribble.com>
"""

class Trie:
    SORT_LENGTH = "length"
    SORT_INSERT_ORDER = "insert_order"

    def __init__(self, data=None):
        if data is None:
            data = {}
        self.data = data
        self.count = 0

    def populate(self, words):
        for word in words:
            datadict = self.data
            for letter in word:
                datadict = datadict.setdefault(letter, {})
            datadict[self.count] = True
            self.count += 1

    def find(self, root, sort_by=None):
        def _expand_subtree(prefix, subtree):
            words = []
            for letter, data in subtree.items():
                if isinstance(letter, int):
                    words.append((prefix, letter))
                else:
                    words.extend(
                        _expand_subtree(prefix + letter, data)
                    )
            return words

        datadict = self.data
        for letter in root:
            if letter not in datadict:
                return [], ''
            datadict = datadict.get(letter)
        
        stem = list(root)
        stemdict = datadict
        while(len(stemdict) == 1):
            key = list(stemdict.keys())[0] 
            if isinstance(key, int):
                break
            stem.append(key)
            stemdict = stemdict[key]
        
        matches = _expand_subtree(root, datadict)
        stem = ''.join(stem)

        if sort_by == Trie.SORT_LENGTH:
            matches = [
                m[0] 
                for m in sorted(matches, key=lambda x: len(x[0]))
            ]
        elif sort_by == Trie.SORT_INSERT_ORDER:
            matches = [
                m[0] 
                for m in sorted(matches, key=lambda x: -x[1])
            ]
        else:
            matches = [m[0] for m in matches]
        return (matches, stem)
