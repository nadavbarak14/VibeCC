# student.spec

description:
A student is someone who can enroll in courses offered by the institution. Each student has a unique identifier assigned upon registration, along with their email address which must be unique across all students. Students have a name and an enrollment status that indicates whether they are currently active, on leave, or have graduated. Only active students may enroll in new courses.

api:
Create a new student with their name and email, receiving back the created student with their assigned identifier. Look up a student by their identifier. Find a student by their email address. Update a student's name or status. List all students, optionally filtered by status. Check whether a student is eligible to enroll in courses based on their current status.

tests:
Creating a student assigns a unique identifier
Creating a student with a duplicate email fails
Looking up a nonexistent student returns nothing
Finding a student by email returns the correct student
Updating a student's name persists the change
Changing status to graduated prevents new enrollments
Listing students with status filter returns only matching students
Active students are eligible for enrollment
Students on leave are not eligible for enrollment
Graduated students are not eligible for enrollment
