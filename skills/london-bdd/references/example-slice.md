# Worked Example — "Place an Order" slice

**Stack:** Node.js · TypeScript · Express · Vitest · Supertest  
**Behaviour:** A customer can place an order; the system saves it and returns the order ID.

---

## Phase 0 — Understand the slice

- **Behaviour:** Place a new order
- **Entry point:** `POST /orders`
- **Outcome:** HTTP 201 with `{ orderId: string }` in body; order persisted in DB
- **Language:** TypeScript / Express / Vitest

---

## Phase 1 — Outer loop: failing acceptance test

```ts
// tests/acceptance/placeOrder.test.ts
import request from 'supertest'
import { buildApp } from '../../src/app'
import { describe, it, expect } from 'vitest'

describe('POST /orders', () => {
  it('returns 201 and an orderId when order data is valid', async () => {
    const app = buildApp()   // ← real wiring, no mocks
    const res = await request(app)
      .post('/orders')
      .send({ item: 'Clean Code', qty: 2 })
    expect(res.status).toBe(201)
    expect(res.body).toHaveProperty('orderId')
  })
})
```

**🔴 AT: Place Order** — fails because `/orders` route doesn't exist yet.

Commit: `test: failing acceptance test — place order`

---

## Phase 2 — Inner loop, iteration 1: OrderHandler

**Collaborator discovered:** `OrderService` (the handler shouldn't contain business logic)

```ts
// tests/unit/OrderHandler.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { OrderHandler } from '../../src/handlers/OrderHandler'
import type { OrderService } from '../../src/ports/OrderService'

describe('OrderHandler', () => {
  let service: OrderService
  let handler: OrderHandler

  beforeEach(() => {
    service = { placeOrder: vi.fn() }
    handler = new OrderHandler(service)
  })

  it('calls OrderService and returns 201 with orderId', async () => {
    ;(service.placeOrder as ReturnType<typeof vi.fn>).mockResolvedValue('ord-1')
    const req = { body: { item: 'Clean Code', qty: 2 } } as any
    const res = { status: vi.fn().mockReturnThis(), json: vi.fn() } as any

    await handler.handle(req, res)

    expect(service.placeOrder).toHaveBeenCalledWith({ item: 'Clean Code', qty: 2 })
    expect(res.status).toHaveBeenCalledWith(201)
    expect(res.json).toHaveBeenCalledWith({ orderId: 'ord-1' })
  })
})
```

**🔴 UT: OrderHandler — calls service and returns 201**

Minimum production code:

```ts
// src/handlers/OrderHandler.ts
import type { OrderService } from '../ports/OrderService'

export class OrderHandler {
  constructor(private readonly service: OrderService) {}

  async handle(req: any, res: any): Promise<void> {
    const orderId = await this.service.placeOrder(req.body)
    res.status(201).json({ orderId })
  }
}
```

**🟢 UT: OrderHandler — calls service and returns 201**  
**🔵 Refactor:** nothing to change yet.  
Commit: `feat: OrderHandler delegates to OrderService`

---

## Phase 2 — Inner loop, iteration 2: OrderService

**Collaborator discovered:** `OrderRepository` (service shouldn't know about persistence)

```ts
// tests/unit/OrderService.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { DefaultOrderService } from '../../src/services/OrderService'
import type { OrderRepository } from '../../src/ports/OrderRepository'

describe('DefaultOrderService', () => {
  let repo: OrderRepository
  let sut: DefaultOrderService

  beforeEach(() => {
    repo = { save: vi.fn() }
    sut = new DefaultOrderService(repo)
  })

  it('saves the order to the repository and returns the generated id', async () => {
    ;(repo.save as ReturnType<typeof vi.fn>).mockResolvedValue('ord-999')
    const id = await sut.placeOrder({ item: 'Clean Code', qty: 2 })
    expect(repo.save).toHaveBeenCalledWith({ item: 'Clean Code', qty: 2 })
    expect(id).toBe('ord-999')
  })
})
```

**🔴 UT: OrderService — saves and returns id**

Minimum production code + ports:

```ts
// src/ports/OrderService.ts
export interface OrderService {
  placeOrder(data: { item: string; qty: number }): Promise<string>
}

// src/ports/OrderRepository.ts
export interface OrderRepository {
  save(data: { item: string; qty: number }): Promise<string>
}

// src/services/OrderService.ts
import type { OrderRepository } from '../ports/OrderRepository'
import type { OrderService } from '../ports/OrderService'

export class DefaultOrderService implements OrderService {
  constructor(private readonly repo: OrderRepository) {}

  async placeOrder(data: { item: string; qty: number }): Promise<string> {
    return this.repo.save(data)
  }
}
```

**🟢 UT: OrderService — saves and returns id**  
Commit: `feat: DefaultOrderService delegates to OrderRepository`

---

## Phase 2 — Inner loop, iteration 3: SqlOrderRepository

This is infrastructure; unit test with a real in-memory SQLite or integration test.  
(No further mocking needed — we own the real implementation.)

---

## Phase 3 — Close the outer loop

Wire everything in the composition root:

```ts
// src/app.ts
import express from 'express'
import { SqlOrderRepository } from './repositories/SqlOrderRepository'
import { DefaultOrderService } from './services/OrderService'
import { OrderHandler } from './handlers/OrderHandler'

export function buildApp() {
  const app = express()
  app.use(express.json())

  const repo    = new SqlOrderRepository()
  const service = new DefaultOrderService(repo)
  const handler = new OrderHandler(service)

  app.post('/orders', (req, res) => handler.handle(req, res))

  return app
}
```

Run acceptance test → **🟢 AT: Place Order**  
Commit: `feat: place order — acceptance test passing`

---

## Collaborator map

```
POST /orders
    └── OrderHandler
            └── DefaultOrderService  (implements OrderService)
                    └── SqlOrderRepository  (implements OrderRepository)
```

Each arrow = interface boundary, mocked in unit tests above it.
