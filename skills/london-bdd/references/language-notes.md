# Language & Framework Testing Notes

## JavaScript / TypeScript (Node.js)

**Recommended stack:**
- Test runner: **Vitest** (fast, ESM-native) or **Jest**
- Mocking: `vi.fn()` / `jest.fn()`, `vi.spyOn()`
- Acceptance tests: **Supertest** (HTTP), **Playwright** / **Cypress** (UI)
- DI: hand-rolled constructor injection or **tsyringe** / **inversify**

**Unit test skeleton (Vitest):**
```ts
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { OrderService } from './OrderService'
import type { OrderRepository } from './ports/OrderRepository'

describe('OrderService', () => {
  let repo: OrderRepository
  let sut: OrderService

  beforeEach(() => {
    repo = { save: vi.fn(), findById: vi.fn() }
    sut = new OrderService(repo)
  })

  it('saves a new order and returns its id', async () => {
    repo.save = vi.fn().mockResolvedValue('order-123')
    const id = await sut.placeOrder({ item: 'book', qty: 1 })
    expect(repo.save).toHaveBeenCalledWith({ item: 'book', qty: 1 })
    expect(id).toBe('order-123')
  })
})
```

**Acceptance test skeleton (Supertest + Vitest):**
```ts
import request from 'supertest'
import { buildApp } from '../src/app'   // wires real dependencies
import { describe, it, expect } from 'vitest'

describe('POST /orders — place order', () => {
  it('returns 201 with the new order id', async () => {
    const app = buildApp()              // no mocks
    const res = await request(app)
      .post('/orders')
      .send({ item: 'book', qty: 1 })
    expect(res.status).toBe(201)
    expect(res.body).toHaveProperty('orderId')
  })
})
```

---

## Python

**Recommended stack:**
- Test runner: **pytest**
- Mocking: `unittest.mock` (`MagicMock`, `patch`), **pytest-mock** (`mocker` fixture)
- Acceptance tests: **httpx** + **FastAPI TestClient**, or **pytest-bdd** for Gherkin
- DI: constructor injection; **dependency-injector** lib for larger projects

**Unit test skeleton (pytest + pytest-mock):**
```python
from unittest.mock import MagicMock
from order_service import OrderService

def test_places_order_and_returns_id(mocker):
    repo = MagicMock()
    repo.save.return_value = "order-123"
    sut = OrderService(repo)

    order_id = sut.place_order(item="book", qty=1)

    repo.save.assert_called_once_with(item="book", qty=1)
    assert order_id == "order-123"
```

**Acceptance test skeleton (FastAPI):**
```python
from fastapi.testclient import TestClient
from app import build_app   # wires real dependencies

def test_place_order_returns_201():
    client = TestClient(build_app())   # no mocks
    response = client.post("/orders", json={"item": "book", "qty": 1})
    assert response.status_code == 201
    assert "orderId" in response.json()
```

---

## Java / Kotlin

**Recommended stack:**
- Test runner: **JUnit 5**
- Mocking: **Mockito** (Java), **MockK** (Kotlin)
- Acceptance tests: **Spring Boot Test** with `@SpringBootTest`, **REST Assured**
- DI: Spring or hand-rolled constructor injection

**Unit test skeleton (Kotlin + MockK):**
```kotlin
@Test
fun `saves order and returns id`() {
    val repo = mockk<OrderRepository>()
    every { repo.save(any()) } returns "order-123"
    val sut = OrderService(repo)

    val id = sut.placeOrder(OrderRequest("book", 1))

    verify(exactly = 1) { repo.save(OrderRequest("book", 1)) }
    id shouldBe "order-123"
}
```

---

## Ruby

**Recommended stack:**
- Test runner: **RSpec**
- Mocking: RSpec built-in doubles (`double`, `instance_double`)
- Acceptance tests: **RSpec + rack-test** or **Cucumber**

**Unit test skeleton:**
```ruby
RSpec.describe OrderService do
  let(:repo) { instance_double(OrderRepository) }
  subject(:sut) { described_class.new(repo) }

  it 'saves the order and returns its id' do
    allow(repo).to receive(:save).and_return('order-123')
    expect(sut.place_order(item: 'book', qty: 1)).to eq('order-123')
    expect(repo).to have_received(:save).with(item: 'book', qty: 1)
  end
end
```

---

## Go

**Recommended stack:**
- Test runner: built-in `testing` package + **testify**
- Mocking: **mockery** (generates mocks from interfaces), **gomock**
- Acceptance tests: `net/http/httptest` package

**Unit test skeleton:**
```go
func TestOrderService_PlacesOrderAndReturnsID(t *testing.T) {
    repo := &MockOrderRepository{}
    repo.On("Save", mock.Anything).Return("order-123", nil)
    sut := NewOrderService(repo)

    id, err := sut.PlaceOrder(OrderRequest{Item: "book", Qty: 1})

    require.NoError(t, err)
    assert.Equal(t, "order-123", id)
    repo.AssertExpectations(t)
}
```
