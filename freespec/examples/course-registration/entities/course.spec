# course.spec

description:
A course represents an educational offering that students can enroll in. Each course has a unique code like CS101, a title describing its content, and a maximum capacity indicating how many students can enroll. Courses have a status indicating whether enrollment is open, closed, or the course has been cancelled. The current enrollment count tracks how many students are currently enrolled. A course cannot accept enrollments beyond its capacity or when enrollment is not open.

api:
Create a new course with its code, title, and capacity. Look up a course by its code. Update a course's title, capacity, or status. List all courses, optionally filtered by status. Check whether a course can accept new enrollments based on its status and remaining capacity. Increment or decrement the enrollment count when students enroll or withdraw.

tests:
Creating a course with a duplicate code fails
Looking up a course by code returns the correct course
Looking up a nonexistent course returns nothing
Updating capacity to less than current enrollment count fails
Closing enrollment prevents new students from enrolling
Cancelled courses cannot accept enrollments
A full course cannot accept new enrollments
A course with available spots can accept enrollments
Incrementing enrollment count reflects in available spots
Decrementing enrollment count increases available spots
