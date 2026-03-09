# Frappe Course Framework

A visual, drag-and-drop course authoring and playing platform built natively on the [Frappe Framework](https://frappeframework.com/) using Vue.js and Vue Flow.

## Features
- **Visual Course Builder**: Drag-and-drop activities (Videos, PDFs, Quizzes, Presentations, Virtual Agents) onto a canvas and connect them to create a learning path.
- **Dynamic Course Player**: A step-by-step player interface for students to navigate through the course content.
- **Rich Embeds**: Automatically handles embedding YouTube/Vimeo videos, PDFs, and external Virtual Agents.
- **Robust State Management**: Tracks student progress, resilient to page reloads, and recovers from "zombie" states (deleted nodes).
- **Native Frappe Integration**: Utilizes standard Frappe DocTypes (`Course`, `Course Enrollment`), file uploads, routing, and access control.

## Installation

This assumes you already have a working Frappe Bench setup.

1. **Get the App**: 
   From your bench directory, run:
   ```bash
   bench get-app https://github.com/neelparekh9/frappe-framework.git
   ```

2. **Install on your Site**:
   Replace `your-site.local` with your actual site name:
   ```bash
   bench --site your-site.local install-app test_project
   ```

3. **Build Frontend Assets**:
   Since the Vue frontend needs to be compiled:
   ```bash
   bench build --app test_project
   ```

4. **Clear Cache & Restart**:
   ```bash
   bench clear-cache
   bench restart
   ```

## How to Access the Course Creator

### 1. Building a Course
1. Log into the Frappe Desk as an Administrator or System Manager.
2. Use the search bar to go to the **Course List**.
3. Create a **New Course**. Give it a Title and save it.
4. Click the **"Open Builder"** button in the top right corner.
5. You are now in the Visual Builder!
   - Drag components from the left sidebar onto the canvas.
   - Click any component to open its configuration modal (upload files, set URLs).
   - Draw connections (arrows) between the components to define the flow.
   - Click the **Save** button in the top right when you are done.

### 2. Taking a Course (Student View)
1. Go to the **Course Enrollment List**.
2. Create a **New Course Enrollment**.
3. Select a **Student** (a Frappe User) and the **Course** you just built.
4. Save the record.
5. Click the **"Open Player"** button in the top right corner. The player will launch and guide the user through the defined steps!

## Tech Stack
- **Backend**: Python, MariaDB, Frappe Framework
- **Frontend Admin**: Vue 3 (Composition API), Vue Flow
- **Scaffolding**: esbuild (Frappe standard)
