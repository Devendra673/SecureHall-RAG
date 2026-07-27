# SECUREHALL-RAG DESIGN DECISIONS
Phase 5B, Task 5B.1.6 - Document Design Decisions

This document records the rationale behind the key design and UX decisions for the SecureHall-RAG portal, including accessibility choices and responsive breakpoints.

---

## 1. Core Architecture Decisions

### 1.1 The Three-Column Layout (Desktop)
*   **Decision:** We adopted a three-column layout (Sidebar + Main Chat + Citation Panel) inspired by Perplexity and Google NotebookLM.
*   **Rationale:** RAG applications are inherently dense with information. Users need to balance 1) Context (what documents are active), 2) The Conversation, and 3) The Evidence. Stacking these vertically or hiding them behind menus increases cognitive load. The three-column layout provides immediate visibility to all three pillars simultaneously on large screens.

### 1.2 "Evidence-First" UI
*   **Decision:** Citations are prominent inline superscripts (e.g., `[1]`), and opening them reveals a dedicated panel rather than a small tooltip.
*   **Rationale:** Trust is the primary value proposition of SecureHall-RAG. Tooltips are transient and hard to read for long excerpts. A dedicated evidence panel allows users to read full paragraphs of source material side-by-side with the AI's summary, directly combating hallucination concerns.

### 1.3 Dark Mode by Default
*   **Decision:** The application offers a true dark mode (`#0F172A`) as a first-class citizen, with deep slate tones rather than pure black.
*   **Rationale:** Our target personas (Researchers, Compliance Officers, Developers) often work long hours and prefer low-strain environments. Deep slate provides better contrast for text than pure black, reducing eye fatigue while maintaining a premium, professional aesthetic.

---

## 2. Component-Level Decisions

### 2.1 Chat Bubbles vs. Streamed Text
*   **Decision:** User inputs are styled as distinct bubbles (right-aligned), while AI responses are styled as document-like blocks or subdued cards (left-aligned).
*   **Rationale:** This creates a clear visual hierarchy. User inputs are short commands; AI outputs are dense, structured information (paragraphs, lists, code). Forcing AI outputs into small "speech bubbles" harms readability.

### 2.2 Shadcn/ui & Tailwind
*   **Decision:** Using Shadcn/ui components customized with TailwindCSS.
*   **Rationale:** Shadcn/ui is not a traditional component library; it gives us direct ownership of the source code for components. This allows for extreme customization (necessary for our specific dark mode and branding) while guaranteeing high accessibility standards out of the box (via Radix UI primitives).

---

## 3. Accessibility Considerations (WCAG 2.1 AA)

We are committed to making SecureHall-RAG accessible to all users.

*   **Color Contrast:** All text (including inline citations) has been verified to meet the `4.5:1` contrast ratio against its background. Brand Blue (`#3B82F6` in dark mode) was chosen specifically because it remains legible on dark backgrounds.
*   **Focus Management:** 
    *   Keyboard users will see a clear `2px solid` focus ring (using Tailwind's `ring` utilities) on all interactive elements.
    *   When modals (like the Citation Panel on mobile) open, focus is automatically trapped inside the modal, and returning focus to the trigger upon closing.
*   **Screen Readers:**
    *   Loading states ("Thinking...") use `aria-live="polite"` to announce when the AI is processing and when the response is ready without interrupting the user.
    *   Citation markers include hidden `sr-only` text (e.g., "Citation 1") so screen readers don't just read "One".
*   **Reduced Motion:** Animations (like sidebar sliding or modal fading) respect the `prefers-reduced-motion` media query.

---

## 4. Responsive Breakpoints

The application uses a mobile-first approach, progressively enhancing the layout for larger screens using standard Tailwind breakpoints.

| Breakpoint | Width | Layout Shift |
| :--- | :--- | :--- |
| **Default (Mobile)** | `< 768px` | Single column. Sidebar is hidden behind a hamburger menu drawer. Citations open as a full-screen bottom sheet/modal. |
| **`md` (Tablet)** | `≥ 768px` | Two columns. Main Chat takes precedence. Sidebar remains a drawer, but Citations can open as a side-by-side panel overlapping the chat slightly. |
| **`lg` (Desktop)** | `≥ 1024px` | Three columns. Sidebar is fixed on the left (240px). Chat is centered. |
| **`xl` (Large Desktop)** | `≥ 1280px` | Three columns. Main Chat width is capped at 800px to prevent lines of text from becoming too long and unreadable. Citations panel is fixed on the right (320px). |

---
**Status**: Completed (Phase 5B, Task 1.6)
**Date**: June 4, 2026
