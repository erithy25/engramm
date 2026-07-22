    def learn_online(self, data: bytes, label) -> bool:
        """Ein T2-Schritt: klassifizieren, bei Fehler Prototypen korrigieren
        und Nuetzlichkeit der abgerufenen Episoden anpassen. True = korrekt."""
        c_true = self._ensure_class(label)
        packed, signed = self.im.encode_signed(data)
        score = self._scores(packed)
        c_pred = int(np.argmax(score))
        for i in self._last_topk:                      # Nuetzlichkeit
            delta = 1 if self.vals[i] == c_true else -1
            self.util[i] = np.clip(self.util[i] + delta, -UTIL_CLIP, UTIL_CLIP)
        if c_pred != c_true:                           # Perceptron-Stil
            self.A[c_true] += signed
            self.A[c_pred] -= signed
            self._rebinarize(c_true)
            self._rebinarize(c_pred)
            return False
        return True
