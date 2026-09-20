Retrieval metrics cover the 52 questions with `expected_behavior=answer`; the rest have no target document.

| Config | Embedding | Chunking | Runs | Machine | doc-hit@5 | MRR | Answers | Err | Trunc | Cut | Context med/max | Answer tok |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `c101` | MiniLM-L6 | flat | 5 | server | 0.981 | 0.735 | 300/300 | 0 | 0 | 1 | 5,126 / 5,128 | 229 |
| `c103` | MiniLM-L6 | hierarchical | 5 | server | 0.942 | 0.825 | 300/300 | 0 | 0 | 0 | 17,880 / 20,908 | 230 |
| `c105` | bge-m3 | flat | 5 | Mac | 1.000 | 0.804 | 300/300 | 0 | 0 | 0 | 5,127 / 5,128 | 205 |
| `c107` | bge-m3 | hierarchical | 5 | Mac | 0.962 | 0.739 | 300/300 | 0 | 0 | 1 | 14,980 / 21,263 | 208 |
