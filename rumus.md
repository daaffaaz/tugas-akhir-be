$$\text{Hit Rate@K} = \frac{1}{|Q|} \sum_{q \in Q} \mathbb{1}\left[|\text{relevant}(q) \cap \text{retrieved}(q, K)| \geq 1\right]$$

$$\text{Precision@K} = \frac{1}{|Q|} \sum_{q \in Q} \frac{|\text{relevant}(q) \cap \text{retrieved}(q, K)|}{K}$$

di mana:
- $Q$ = himpunan test query.
- $\text{relevant}(q)$ = himpunan course relevan untuk query $q$ (dari ground truth).
- $\text{retrieved}(q, K)$ = himpunan $K$ course teratas yang dikembalikan retriever.
