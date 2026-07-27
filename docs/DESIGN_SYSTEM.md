# SECUREHALL-RAG DESIGN SYSTEM
Phase 5B, Task 5B.1.4 - Define Design System

This document outlines the core design tokens, component specifications, and styling rules for the SecureHall-RAG web portal. This system is designed to be fully compatible with **TailwindCSS** and **Shadcn/ui**.

---

## 1. COLOR PALETTE

We use a dual-theme (Light/Dark) approach. Colors should be implemented using CSS variables mapping to Tailwind utility classes.

### 1.1 Brand Colors
*   **Primary (Brand Blue):** The main interactive color used for primary buttons, active states, and focus rings.
    *   Light Mode: `#0066CC` (Tailwind: `blue-600`)
    *   Dark Mode: `#3B82F6` (Tailwind: `blue-500`)
*   **Secondary (Modern Purple):** Used for AI response bubbles and secondary emphasis.
    *   Light Mode: `#6C63FF` (Tailwind: `indigo-500`)
    *   Dark Mode: `#8B5CF6` (Tailwind: `violet-500`)
*   **Accent/Destructive:** Used for destructive actions (delete) or urgent alerts.
    *   Light Mode: `#EF4444` (Tailwind: `red-500`)
    *   Dark Mode: `#F87171` (Tailwind: `red-400`)

### 1.2 Surface Colors (Backgrounds & Cards)
*   **Background (App Base):**
    *   Light Mode: `#F8FAFC` (Tailwind: `slate-50`)
    *   Dark Mode: `#0F172A` (Tailwind: `slate-950`)
*   **Surface (Cards, Modals, Chat Bubbles):**
    *   Light Mode: `#FFFFFF` (Tailwind: `white`)
    *   Dark Mode: `#1E293B` (Tailwind: `slate-800`)
*   **Surface Alternate (Sidebar, Citation Panel):**
    *   Light Mode: `#F1F5F9` (Tailwind: `slate-100`)
    *   Dark Mode: `#111827` (Tailwind: `gray-900`)

### 1.3 Text & Borders
*   **Text Primary:**
    *   Light Mode: `#0F172A` (Tailwind: `slate-950`)
    *   Dark Mode: `#F8FAFC` (Tailwind: `slate-50`)
*   **Text Secondary (Muted):**
    *   Light Mode: `#64748B` (Tailwind: `slate-500`)
    *   Dark Mode: `#94A3B8` (Tailwind: `slate-400`)
*   **Borders & Dividers:**
    *   Light Mode: `#E2E8F0` (Tailwind: `slate-200`)
    *   Dark Mode: `#334155` (Tailwind: `slate-700`)

### 1.4 Status Colors
*   **Success (High Confidence):** `#10B981` (emerald-500)
*   **Warning (Medium Confidence):** `#F59E0B` (amber-500)
*   **Error (Low Confidence/Failures):** `#EF4444` (red-500)

---

## 2. TYPOGRAPHY SCALE

We use **Inter** as the primary font family for a clean, modern, and highly legible interface. **Monaco** or **Courier New** is used for code blocks and raw citations.

*   **Font Family Sans:** `'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`
*   **Font Family Mono:** `'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', monospace`

### Heading Scale
*   **H1 (Page Titles):** 28px (1.75rem), Font Weight: 700 (Bold), Line Height: 1.2
*   **H2 (Section Headers):** 24px (1.5rem), Font Weight: 600 (Semibold), Line Height: 1.3
*   **H3 (Card/Panel Headers):** 20px (1.25rem), Font Weight: 600 (Semibold), Line Height: 1.4
*   **H4 (Small Labels):** 14px (0.875rem), Font Weight: 600 (Semibold), Line Height: 1.5, Uppercase

### Body Scale
*   **Body Large:** 18px (1.125rem) — Used for introductory text or standalone paragraphs.
*   **Body Default:** 16px (1rem) — Primary size for chat messages and standard text. Line Height: 1.6
*   **Body Small:** 14px (0.875rem) — Used for secondary text, metadata, sidebar items. Line Height: 1.5
*   **Caption (Micro):** 12px (0.75rem) — Used for timestamps, citation markers, tooltips.

---

## 3. SPACING & LAYOUT SCALE

Spacing follows an 8px modular grid.

*   `0.25rem` (4px) - Micro spacing (e.g., between an icon and text)
*   `0.5rem` (8px) - Tight spacing (e.g., inside small buttons or badges)
*   `0.75rem` (12px) - Standard inner padding for inputs and list items
*   `1rem` (16px) - Default spacing (e.g., card padding, chat bubble padding)
*   `1.5rem` (24px) - Medium spacing (e.g., between major components)
*   `2rem` (32px) - Section spacing
*   `3rem` (48px) - Large layout gaps

### Layout Constraints
*   **Max Content Width:** 1440px
*   **Sidebar Width:** 240px - 280px
*   **Citation Panel Width:** 320px - 380px
*   **Chat Container Max Width:** 800px (to maintain readability)

---

## 4. COMPONENT LIBRARY SPECIFICATION

We will utilize **Shadcn/ui** to build these components, heavily relying on its accessible Radix UI primitives.

### 4.1 Buttons (`<Button>`)
*   **Primary:** Solid Brand Blue background, white text. No border.
*   **Secondary:** Outline style. Transparent background, border colored `slate-300` (light) or `slate-700` (dark), text primary color.
*   **Ghost:** No background, no border. Subtle background color on hover.
*   **Corner Radius (Radius):** 8px (`rounded-lg`) for a modern, friendly look.

### 4.2 Inputs & Textareas (`<Input>`, `<Textarea>`)
*   **Background:** Matches surface color.
*   **Border:** 1px solid default border color.
*   **Focus State:** 2px solid Brand Blue ring (`ring-2 ring-blue-500`).
*   **Padding:** 12px horizontal, 12px vertical.
*   **Corner Radius:** 8px (`rounded-lg`).

### 4.3 Chat Bubbles
*   **User Message:** Brand Blue background, White text, rounded corners (16px) with the bottom-right corner slightly less rounded (4px) to indicate direction.
*   **AI Message:** Surface color background (e.g., `slate-800` in dark mode), primary text color, rounded corners (16px) with bottom-left corner slightly less rounded (4px). Include subtle shadow `shadow-sm`.

### 4.4 Citations (`<Badge>`, Hover Cards)
*   **Inline Citation Marker:** Small, blue background, white text pill. Size: 18px x 18px. Clickable.
*   **Citation Source Card:** Surface alternate background. Left-bordered with a 3px thick colored accent line (matching confidence level: green/yellow/red).

### 4.5 Modals & Dialogs (`<Dialog>`)
*   **Overlay:** Black background with 50% opacity (`bg-black/50`) and subtle backdrop blur (`backdrop-blur-sm`).
*   **Content Container:** Surface background color, rounded 12px (`rounded-xl`), large shadow (`shadow-xl`), standard 24px padding.

### 4.6 Shadows & Elevation
*   **Sm (`shadow-sm`):** Buttons, inputs, chat bubbles.
*   **Md (`shadow-md`):** Cards, dropdown menus.
*   **Lg (`shadow-lg`):** Modals, popovers, floating citation panels.

---
**Status**: Completed (Phase 5B, Task 1.4)
**Date**: June 4, 2026
