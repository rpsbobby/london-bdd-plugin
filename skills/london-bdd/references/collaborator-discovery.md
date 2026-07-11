# Collaborator Discovery Heuristics

In London School BDD, you don't design collaborators upfront.
You **discover** them by asking: "What does this object need to do its job?"

---

## The three questions

When implementing a class, ask after each responsibility:

1. **"Does this belong here?"**  
   If the logic is outside the object's core purpose, it belongs in a collaborator.

2. **"What role name describes what I need?"**  
   Name by *capability*, not by implementation. `EmailSender` not `SendGridClient`.

3. **"What is the minimal interface for that role?"**  
   Define only the method(s) you actually call. Start with one method.

---

## Smell signals that a collaborator is needed

| Smell | Collaborator to introduce |
|---|---|
| Talking to a database / external API | `Repository`, `Gateway`, `Client` |
| Sending notifications | `Notifier`, `Emailer`, `Publisher` |
| Formatting / rendering output | `Formatter`, `Renderer`, `Presenter` |
| Logging / auditing | `Logger`, `AuditLog` |
| Generating IDs / timestamps | `IdGenerator`, `Clock` |
| Complex domain calculation reused elsewhere | Extract to a **Value Object** or **Domain Service** |

---

## Naming conventions

| Role type | Naming pattern |
|---|---|
| Data access | `*Repository`, `*Store`, `*Dao` |
| External service | `*Gateway`, `*Client`, `*Adapter` |
| Side effect | `*Sender`, `*Publisher`, `*Notifier` |
| Query | `*Finder`, `*Reader`, `*Fetcher` |
| Factory | `*Factory`, `*Builder`, `*Creator` |

---

## Too many collaborators?

If a class has more than **3–4 collaborators**, it may be doing too much.  
Options:
- Extract a **Facade** that wraps related collaborators.
- Split the class by responsibility (SRP).
- Reconsider the slice — maybe it's too big.

---

## Collaborator chain depth

London School naturally creates shallow chains. If you're going more than
3 levels deep (A → B → C → D), pause and ask:
- Is the slice too large?
- Can the outer class talk directly to a lower collaborator?
- Is there a missing abstraction that shortens the chain?

---

## Mock or don't mock?

The discriminator is **peer vs internal** (see the doubling principle in
the skill): double what the unit *talks to*, keep real what it *owns*.

| Collaborator type | Mock in unit test? |
|---|---|
| Your own interfaces/ports | ✅ Always |
| Third-party library (HTTP client, ORM) | ❌ Wrap it first, then mock the wrapper |
| Value objects / pure functions | ❌ Use the real thing |
| In-process domain services (no I/O) | ❌ Prefer real; mock only if slow |
| Time / randomness | ✅ Mock via `Clock` / `IdGenerator` interfaces |
