# Frappe Course Framework

A visual, drag-and-drop course authoring and playing platform built natively on the [Frappe Framework](https://frappeframework.com/) using Vue.js and Vue Flow.

## Features
- **Visual Course Builder**: Drag-and-drop activities (Videos, PDFs, Quizzes, Presentations, Virtual Agents) onto a canvas and connect them to create a learning path.
- **Dynamic Course Player**: A step-by-step player interface for students to navigate through the course content.
- **Rich Embeds**: Automatically handles embedding YouTube/Vimeo videos, PDFs, and external Virtual Agents.
- **Robust State Management**: Tracks student progress, resilient to page reloads, and recovers from "zombie" states (deleted nodes).
- **Native Frappe Integration**: Utilizes standard Frappe DocTypes (`Course`, `Course Enrollment`), file uploads, routing, and access control.

## How to Run and Access the Course Creator

1. Clone the directory to your local machine.
2. Open your terminal and navigate to the frappe-bench directory:
   ```bash
   cd frappe
   cd frappe-bench
   ```
3. Start the bench server:
   ```bash
   bench start
   ```
4. Once the server is running, access the course creator by visiting this link:
   [http://127.0.0.1:8001/desk/course/Test%20Course](http://127.0.0.1:8001/desk/course/Test%20Course)

## Tech Stack
- **Backend**: Python, MariaDB, Frappe Framework
- **Frontend Admin**: Vue 3 (Composition API), Vue Flow
- **Scaffolding**: esbuild (Frappe standard)
