# 🎨 FIGMA DESIGN TEMPLATES - AI Agent Platform

Complete design system and screen templates for Figma customization.

---

## 📋 **TABLE OF CONTENTS**

1. [Design System](#design-system)
2. [Component Library](#component-library)
3. [Screen Templates](#screen-templates)
4. [Figma Setup Guide](#figma-setup-guide)
5. [Export Guidelines](#export-guidelines)

---

## 🎨 **DESIGN SYSTEM**

### **Color Palette**

#### Primary Colors (Blue)
```
primary-50:  #f0f9ff  (Backgrounds)
primary-100: #e0f2fe  (Light accents)
primary-200: #bae6fd  
primary-300: #7dd3fc  
primary-400: #38bdf8  
primary-500: #0ea5e9  (Links, CTAs)
primary-600: #0284c7  (Primary buttons)
primary-700: #0369a1  (Primary button hover)
primary-800: #075985  
primary-900: #0c4a6e  
```

#### Neutral Colors (Gray)
```
dark-50:  #f8fafc  (Page background)
dark-100: #f1f5f9  (Card background)
dark-200: #e2e8f0  (Borders)
dark-300: #cbd5e1  
dark-400: #94a3b8  
dark-500: #64748b  (Muted text)
dark-600: #475569  (Secondary text)
dark-700: #334155  
dark-800: #1e293b  
dark-900: #0f172a  (Primary text)
```

#### Status Colors
```
Success:
- Green-100: #dcfce7
- Green-600: #16a34a
- Green-800: #166534

Warning:
- Yellow-100: #fef3c7
- Yellow-600: #d97706
- Yellow-800: #92400e

Error:
- Red-100: #fee2e2
- Red-600: #dc2626
- Red-800: #991b1b

Info:
- Blue-100: #dbeafe
- Blue-600: #2563eb
- Blue-800: #1e40af
```

### **Typography**

#### Font Families
```
Primary: Inter
- Light (300)
- Regular (400)
- Medium (500)
- Semibold (600)
- Bold (700)

Monospace: JetBrains Mono
- Regular (400)
- Medium (500)
```

#### Font Sizes
```
xs:   0.75rem (12px)  - Captions, labels
sm:   0.875rem (14px) - Secondary text
base: 1rem (16px)     - Body text
lg:   1.125rem (18px) - Large body
xl:   1.25rem (20px)  - Small headings
2xl:  1.5rem (24px)   - Section headings
3xl:  1.875rem (30px) - Page titles
4xl:  2.25rem (36px)  - Hero text
```

### **Spacing Scale**
```
0.5: 0.125rem (2px)
1:   0.25rem (4px)
2:   0.5rem (8px)
3:   0.75rem (12px)
4:   1rem (16px)
5:   1.25rem (20px)
6:   1.5rem (24px)
8:   2rem (32px)
10:  2.5rem (40px)
12:  3rem (48px)
16:  4rem (64px)
20:  5rem (80px)
```

### **Border Radius**
```
sm:   0.125rem (2px)
base: 0.25rem (4px)
md:   0.375rem (6px)
lg:   0.5rem (8px)
xl:   0.75rem (12px)
2xl:  1rem (16px)
full: 9999px (circle)
```

### **Shadows**
```
sm:   0 1px 2px 0 rgb(0 0 0 / 0.05)
base: 0 1px 3px 0 rgb(0 0 0 / 0.1)
md:   0 4px 6px -1px rgb(0 0 0 / 0.1)
lg:   0 10px 15px -3px rgb(0 0 0 / 0.1)
xl:   0 20px 25px -5px rgb(0 0 0 / 0.1)
```

---

## 🧩 **COMPONENT LIBRARY**

### **1. Buttons**

#### Primary Button
```
State: Default
- Background: primary-600 (#0284c7)
- Text: White (font-medium)
- Padding: 16px 24px (py-4 px-6)
- Border-radius: 8px (lg)
- Shadow: sm

State: Hover
- Background: primary-700 (#0369a1)
- Shadow: md

State: Active
- Background: primary-800 (#075985)

State: Disabled
- Background: primary-600 (50% opacity)
- Cursor: not-allowed
```

#### Secondary Button
```
State: Default
- Background: dark-200 (#e2e8f0)
- Text: dark-900 (#0f172a)
- Padding: 16px 24px
- Border-radius: 8px

State: Hover
- Background: dark-300 (#cbd5e1)
```

#### Outline Button
```
State: Default
- Background: Transparent
- Border: 2px solid dark-300
- Text: dark-700
- Padding: 14px 22px (compensate for border)
- Border-radius: 8px

State: Hover
- Background: dark-100
```

### **2. Cards**

```
Container:
- Background: White (#ffffff)
- Border: 1px solid dark-200
- Border-radius: 12px (xl)
- Padding: 24px (p-6)
- Shadow: sm

Card Header:
- Font-size: xl (20px)
- Font-weight: semibold (600)
- Color: dark-900
- Margin-bottom: 16px

Card Body:
- Font-size: base (16px)
- Color: dark-600
- Line-height: 1.5
```

### **3. Input Fields**

```
State: Default
- Background: White
- Border: 1px solid dark-300
- Border-radius: 8px
- Padding: 10px 16px
- Font-size: base (16px)

State: Focus
- Border: 2px solid primary-500
- Outline: None
- Shadow: 0 0 0 3px primary-100 (ring)

State: Error
- Border: 2px solid red-600
- Ring: red-100

With Label:
- Label font-size: sm (14px)
- Label font-weight: medium (500)
- Label color: dark-700
- Label margin-bottom: 4px
```

### **4. Badges**

#### Success Badge
```
- Background: green-100
- Text: green-800
- Padding: 2px 10px (py-0.5 px-2.5)
- Border-radius: full
- Font-size: xs (12px)
- Font-weight: medium (500)
```

#### Warning Badge
```
- Background: yellow-100
- Text: yellow-800
- (same spacing as above)
```

#### Error Badge
```
- Background: red-100
- Text: red-800
```

#### Info Badge
```
- Background: blue-100
- Text: blue-800
```

### **5. Navigation**

#### Top Navigation Bar
```
Container:
- Background: White
- Border-bottom: 1px solid dark-200
- Height: 64px
- Sticky position: top

Logo Area:
- Icon size: 40px x 40px
- Background: primary-600
- Border-radius: 8px
- Title font-size: lg (18px)
- Title font-weight: bold (700)

Nav Links:
- State Default:
  - Color: dark-600
  - Padding: 8px 16px
  - Border-radius: 8px
  - Font-size: base

- State Active:
  - Background: primary-50
  - Color: primary-700
  - Font-weight: medium
```

### **6. Data Tables**

```
Table Header:
- Background: dark-100
- Border-bottom: 2px solid dark-200
- Padding: 12px 16px
- Font-size: sm (14px)
- Font-weight: semibold (600)
- Color: dark-700

Table Row:
- Border-bottom: 1px solid dark-200
- Padding: 16px
- Font-size: sm (14px)

- State Hover:
  - Background: dark-50

Table Cell:
- Color: dark-900 (primary content)
- Color: dark-600 (secondary content)
```

---

## 📱 **SCREEN TEMPLATES**

### **1. Login Page**

**Layout:**
```
┌────────────────────────────────────┐
│                                    │
│           [Logo Icon]              │
│       AI Agent Platform            │
│  Competitive Intelligence with AI  │
│                                    │
│  ┌──────────────────────────────┐ │
│  │       Welcome Back           │ │
│  │                              │ │
│  │  Email:    [______________]  │ │
│  │  Password: [______________]  │ │
│  │                              │ │
│  │  [    Sign In Button     ]   │ │
│  │                              │ │
│  │  Don't have account? Sign up │ │
│  └──────────────────────────────┘ │
│                                    │
└────────────────────────────────────┘
```

**Colors:**
- Background: Gradient from primary-50 to primary-100
- Card: White with xl shadow
- Logo icon: 64px x 64px, primary-600, rounded-2xl

### **2. Dashboard Page**

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│ [Logo] AI Agent Platform          [User Avatar ▾]      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Dashboard                    [+ New Master Agent]      │
│  Welcome back! Here's what's happening...              │
│                                                         │
│  ┌───────┐  ┌───────┐  ┌───────┐  ┌───────┐          │
│  │ 🤖 3  │  │ 👥 127│  │📈 450 │  │ 📄 12 │          │
│  │Masters│  │Slaves │  │Keywrds│  │Reports│          │
│  └───────┘  └───────┘  └───────┘  └───────┘          │
│                                                         │
│  ┌─────────────────────────────────────────────┐       │
│  │ Recent Workflows                            │       │
│  │                                             │       │
│  │  ✅ daibau.ro - Completed (13 slaves)       │       │
│  │  ⏳ example.ro - In Progress (45%)          │       │
│  │  ✅ another.ro - Completed (8 slaves)       │       │
│  └─────────────────────────────────────────────┘       │
│                                                         │
│  [Quick Action Cards]                                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### **3. Master Agents List**

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│ Master Agents                [+ New Master Agent]       │
│ Manage your AI agents and their competitive intel...    │
│                                                         │
│  ┌─────────────────────────────────────────────┐       │
│  │ 🔍 [Search agents by domain...            ] │       │
│  └─────────────────────────────────────────────┘       │
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │ daibau.ro   │  │ example.ro  │  │ another.ro  │    │
│  │ Construcții │  │ Design      │  │ E-commerce  │    │
│  │             │  │             │  │             │    │
│  │ 👥 13 Slaves│  │ 👥 8 Slaves │  │ 👥 21 Slaves│    │
│  │ #️⃣ 45 Keys  │  │ #️⃣ 32 Keys  │  │ #️⃣ 67 Keys  │    │
│  │ 🤖 266 Chnks│  │ 🤖 189 Chnks│  │ 🤖 342 Chnks│    │
│  │             │  │             │  │             │    │
│  │ ✅ Active   │  │ ⏳ Process. │  │ ✅ Active   │    │
│  │ [Details →] │  │ [Details →] │  │ [Details →] │    │
│  └─────────────┘  └─────────────┘  └─────────────┘    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### **4. Agent Detail Page**

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│ ← Back                                                   │
│                                                         │
│  🏢 daibau.ro [🔗]                         ✅ Active    │
│  Construcții & Renovări                                 │
│                                                         │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐       │
│  │  266   │  │   13   │  │   45   │  │Nov 10  │       │
│  │ Chunks │  │ Slaves │  │Keywrds │  │Created │       │
│  └────────┘  └────────┘  └────────┘  └────────┘       │
│                                                         │
│  ┌─────────────────────────────────────────────┐       │
│  │ MASTER-SLAVE ORGANOGRAM                     │       │
│  │                                             │       │
│  │           ┌──────────────┐                  │       │
│  │           │  daibau.ro   │                  │       │
│  │           │   (MASTER)   │                  │       │
│  │           └──────┬───────┘                  │       │
│  │      ┌───────┬──┴───┬────────┐             │       │
│  │      │       │      │        │             │       │
│  │  ┌───▼─┐ ┌──▼──┐ ┌─▼───┐ ┌──▼───┐         │       │
│  │  │s1✅│ │s2✅ │ │s3✅ │ │s4⏳ │ ...     │       │
│  │  │823 │ │736  │ │421  │ │...  │         │       │
│  │  └────┘ └─────┘ └─────┘ └─────┘         │       │
│  └─────────────────────────────────────────────┘       │
│                                                         │
│  💡 Master Learning Insights                            │
│  • Discovered 13 competitors in industry                │
│  • Average SERP position: #4.2                          │
│  • Strongest keyword: "renovare apartament" (#2)        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### **5. Workflow Progress Page**

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│ Workflow: daibau.ro                                     │
│ Status: ⏳ In Progress                                  │
│                                                         │
│  Overall Progress    [██████████░░░░░░░░░░] 73%        │
│                                                         │
│  ┌─────────────────────────────────────────────┐       │
│  │ ✅ Phase 1: Master Agent Created            │       │
│  │    Master agent successfully created        │       │
│  └─────────────────────────────────────────────┘       │
│                                                         │
│  ┌─────────────────────────────────────────────┐       │
│  │ ✅ Phase 2: LangChain Integration           │       │
│  │    LangChain orchestration configured       │       │
│  └─────────────────────────────────────────────┘       │
│                                                         │
│  ┌─────────────────────────────────────────────┐       │
│  │ ⏳ Phase 8: Slave Creation                  │   42% │
│  │    Creating slave agents (23/279)           │       │
│  │    └─ ETA: ~6.5 hours                       │       │
│  │    └─ Current: hornbach.ro (736 chunks)     │       │
│  └─────────────────────────────────────────────┘       │
│                                                         │
│  ⏸️  Phase 9: Master Learning (pending)                │
│  ⏸️  Phase 10: Organogram Generation (pending)         │
│                                                         │
│  📊 Live Stats:                                         │
│  • Total chunks: 18,456                                 │
│  • GPU utilization: 87%                                 │
│  • API calls: 1,234                                     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 🛠️ **FIGMA SETUP GUIDE**

### **Step 1: Create New Figma File**

1. Go to [Figma.com](https://figma.com)
2. Create account (free tier is fine)
3. Create new Design file: "AI Agent Platform"

### **Step 2: Setup Design System**

1. **Create Color Styles:**
   - Click "+" → "Color Style"
   - Name: `primary-600`, `dark-900`, etc.
   - Add all colors from palette above

2. **Create Text Styles:**
   - Click "+" → "Text Style"
   - Name: `Heading/3XL`, `Body/Base`, `Caption/XS`, etc.
   - Set font, size, weight, line-height

3. **Create Effect Styles (Shadows):**
   - Click "+" → "Effect Style"
   - Name: `Shadow/SM`, `Shadow/MD`, etc.
   - Add drop shadow with values from above

### **Step 3: Create Components**

1. **Button Component:**
   - Create rectangle with text
   - Add auto-layout (Shift+A)
   - Create variants: Primary, Secondary, Outline
   - Create states: Default, Hover, Disabled

2. **Card Component:**
   - Create frame with white background
   - Add border + shadow
   - Make component with variants

3. **Input Component:**
   - Create frame with border
   - Add placeholder text
   - Create variants for states

4. **Badge Component:**
   - Small rectangle with rounded corners
   - Create variants for success, warning, error

### **Step 4: Design Screens**

1. Create frames for each screen (use templates above)
2. Use components from library
3. Add content and imagery
4. Create prototypes (link screens together)

### **Step 5: Organize & Document**

1. Use pages to separate:
   - Design System
   - Components
   - Screens
   - Prototypes

2. Add descriptions to components
3. Document spacing, colors, usage

---

## 📤 **EXPORT GUIDELINES**

### **For Development:**

1. **Icons:**
   - Export as SVG
   - Remove fills (use currentColor)
   - Optimize with SVGO

2. **Images:**
   - Export as PNG (2x for retina)
   - Or use WebP for smaller size
   - Optimize with TinyPNG

3. **CSS Values:**
   - Use Figma Inspect panel
   - Copy CSS values directly
   - Match with Tailwind classes

### **Figma Plugins to Use:**

1. **Iconify** - Import thousands of icons
2. **Unsplash** - Free stock photos
3. **Lorem Ipsum** - Generate placeholder text
4. **Stark** - Check accessibility/contrast
5. **Figma to Code** - Generate React components

---

## 🎯 **CUSTOMIZATION TIPS**

### **Branding:**

1. Replace primary-600 with your brand color
2. Adjust all primary-* shades accordingly
3. Use color theory (complementary, analogous)

### **Typography:**

1. Choose 1-2 fonts maximum
2. Establish clear hierarchy (6 text styles)
3. Maintain consistency across all screens

### **Spacing:**

1. Use 8px grid system (multiples of 8)
2. Consistent padding/margins
3. Align elements to grid

### **Imagery:**

1. Use consistent illustration style
2. High-quality photos only
3. Optimize for web (< 200KB per image)

---

## 📚 **RESOURCES**

### **Learning:**
- [Figma Tutorial](https://www.figma.com/resources/learn-design/)
- [Refactoring UI](https://www.refactoringui.com/)
- [Laws of UX](https://lawsofux.com/)

### **Inspiration:**
- [Dribbble](https://dribbble.com/)
- [Behance](https://www.behance.net/)
- [Mobbin](https://mobbin.com/)

### **Assets:**
- [Heroicons](https://heroicons.com/)
- [Lucide Icons](https://lucide.dev/)
- [Unsplash](https://unsplash.com/)
- [Undraw Illustrations](https://undraw.co/)

---

## ✅ **QUICK START CHECKLIST**

- [ ] Create Figma account
- [ ] Setup color palette (20 colors)
- [ ] Create text styles (6-8 styles)
- [ ] Create button component with variants
- [ ] Create card component
- [ ] Design login page
- [ ] Design dashboard page
- [ ] Design agents list page
- [ ] Add responsive breakpoints (mobile/tablet/desktop)
- [ ] Create prototype links
- [ ] Share with development team

---

**NEXT:** Import this design system into React using the frontend code we just created! 🚀

