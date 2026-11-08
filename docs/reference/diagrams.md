# Diagrams

These diagrams are **generated from the source code on every docs build**, so they always
reflect the current structure. For the intended design and the reasoning behind it, see
[Explanation](../explanation/index.md).

```python exec="on"
import sys; sys.path.insert(0, "tools/docs")
import gen_diagrams; print(gen_diagrams.render_from_env())
```
