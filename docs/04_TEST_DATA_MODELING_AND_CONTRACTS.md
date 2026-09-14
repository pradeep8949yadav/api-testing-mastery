# Module 04: Test Data Modeling (`dict` vs `dataclass` vs `Pydantic`)

## 1. Why Plain `dict` Fails at Scale in Automation Suites
* **Silent Typos**: `payload["prioirty"]` is silently accepted by Python at runtime; fails downstream on the network or returns ambiguous 400 errors.
* **No IDE Autocomplete**: Developers and SDETs have to guess field names, types, and nesting structures.
* **Fragile Response Parsing**: Deeply nested index/key lookups (`response["data"]["user"]["roles"][0]`) crash tests with `KeyError` or `TypeError: 'NoneType' object is not subscriptable` when responses vary.

---

## 2. Comparison Matrix

| Capability | Plain `dict` | `dataclass` | `Pydantic` (`BaseModel`) |
| :--- | :--- | :--- | :--- |
| **Object Dot-Access** | ❌ No | ✅ Yes (`user.email`) | ✅ Yes (`user.email`) |
| **IDE Autocomplete** | ❌ No | ✅ Yes | ✅ Yes |
| **Runtime Type Enforcement** | ❌ None | ❌ None (visual hints only) | ✅ **Strict Enforcement** |
| **Validation Rules** | ❌ Manual boilerplate | ❌ Manual boilerplate | ✅ `@field_validator`, boundary checks |
| **Schema/Contract Export** | ❌ No | ❌ No | ✅ `model_json_schema()` |
| **Breaking-Change Detection** | ❌ Delayed to assertions | ❌ Silent pass | ✅ **Immediate `ValidationError`** |

---

## 3. Detecting Contract-Breaking Changes Early
When backend teams rename fields or change types without notice:
```python
# If backend changes 'department' to 'team_name':
with pytest.raises(ValidationError):
    UserResponse.model_validate(backend_response)
```
The test suite fails immediately with an unambiguous diagnostic:
`Field 'department' is required but missing from response!`
This enables true Consumer-Driven Contract Validation inside integration and API regression suites.
