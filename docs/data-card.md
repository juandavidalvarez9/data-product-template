# Data card

This card describes the data the project reads. A test checks that the
**Fields** table matches the data contract in `src/data_product/pipeline.py`,
so the two cannot drift apart.

## Source

| | |
| --- | --- |
| Files | `tests/data/products.csv` and `tests/data/products_broken.csv` |
| Origin | Written by hand for the tests. The rows are invented and describe no real product. |
| License | Same as the code: [MIT](../LICENSE) |
| Updated | Only when the tests need it |

## Fields

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `product_id` | BIGINT | yes | Identifier of the product |
| `name` | VARCHAR | yes | Product name |
| `registered_on` | DATE | no | Date the product was registered, written as `2024-01-15` |
| `units` | BIGINT | no | Units in one package |

A required field may not be empty. An empty optional field is written as null.

## Size

`products.csv` has 5 rows. `products_broken.csv` breaks the contract on
purpose: an empty name, a date in the wrong format and text where a number
should be.

## Known problems and bias

- The rows are invented, so they tell you nothing about real products.
- Names mix Spanish and English and include accented letters on purpose, to
  test that UTF-8 text survives the pipeline.

## How to refresh it

Edit the files by hand, then run `uv run poe check`.
