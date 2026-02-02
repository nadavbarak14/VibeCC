# course.spec

## Description
A course available for enrollment.

Properties: id, code (unique), title, capacity, prerequisites (list of course IDs),
status (draft/open/closed/archived), createdAt, updatedAt.

Prerequisites must be completed before a @entities/student can enroll.
Cannot have circular prerequisite chains.

## API
- create(code, title, capacity, prerequisites) -> Course
  Creates course. Code must be unique.

- get(id) -> Course | null
  Returns course or null if not found.

- update(id, updates) -> Course
  Updates course. Cannot reduce capacity below current enrollment.

- delete(id) -> bool
  Archives course. Fails if has active @entities/registration.

- list(filters, pagination) -> list[Course]
  Returns filtered, paginated courses.

- getPrerequisites(id) -> list[Course]
  Returns prerequisite courses.

- checkCapacity(id) -> CapacityInfo
  Returns enrollment count and remaining slots.

- openRegistration(id) -> Course
  Sets status to open.

- closeRegistration(id) -> Course
  Sets status to closed.

## Tests
- Create with valid data succeeds
- Duplicate code rejected
- Invalid prerequisite rejected
- Circular prerequisites rejected
- Get returns course by ID
- Update changes fields
- Cannot reduce capacity below enrollment
- Delete archives course
- Delete fails with active registrations
- Check capacity returns accurate count
