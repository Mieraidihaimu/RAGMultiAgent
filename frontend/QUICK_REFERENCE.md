# Quick Reference Card 🌞

## One-Minute Cheat Sheet

### Include CSS
```html
<link rel="stylesheet" href="summer-theme.css">
```

### Colors
```css
--color-coral: #FF6B6B      /* Primary warm */
--color-peach: #FF8E53      /* Accent warm */
--color-yellow: #FFC93C     /* Highlight */
--color-teal: #4ECDC4       /* Secondary cool */
--color-sky: #5DADE2        /* Info */
--color-text-dark: #2C3E50  /* Main text */
--color-text-medium: #666   /* Secondary text */
--color-bg-white: #FFFFFF   /* Card background */
```

### Buttons
```html
<button class="btn btn-primary">Primary</button>
<button class="btn btn-secondary">Secondary</button>
<button class="btn btn-teal">Teal</button>
```

### Cards
```html
<div class="card">Standard</div>
<div class="card card-warm">Highlighted</div>
```

### Inputs
```html
<input class="input" type="text">
<textarea class="input"></textarea>
<select class="input"></select>
```

### Badges
```html
<span class="badge badge-success">Success</span>
<span class="badge badge-warning">Warning</span>
<span class="badge badge-info">Info</span>
<span class="badge badge-primary">Primary</span>
```

### Text
```html
<h1 class="gradient-text">Gradient Heading</h1>
<p class="text-medium">Secondary text</p>
<p class="text-light">Light text</p>
```

### Spacing
```css
--space-xs: 0.5rem   /* 8px */
--space-sm: 0.75rem  /* 12px */
--space-md: 1rem     /* 16px */
--space-lg: 1.5rem   /* 24px */
--space-xl: 2rem     /* 32px */
```

### Border Radius
```css
--radius-sm: 8px
--radius-md: 12px
--radius-lg: 16px
--radius-xl: 20px
--radius-full: 9999px
```

### Shadows
```css
--shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.04);
--shadow-md: 0 4px 12px rgba(0, 0, 0, 0.08);
--shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.12);
--shadow-warm: 0 8px 32px rgba(255, 142, 83, 0.1);
```

### Gradients
```css
/* Primary warm */
linear-gradient(135deg, #FF6B6B 0%, #FFC93C 100%)

/* Secondary cool */
linear-gradient(135deg, #4ECDC4 0%, #5DADE2 100%)

/* Hero text */
linear-gradient(135deg, #2C3E50 0%, #FF6B6B 50%, #FFC93C 100%)

/* Background */
linear-gradient(135deg, #FFF5E6 0%, #FFF9F0 50%, #F0F9FF 100%)
```

### Common Patterns
```html
<!-- Header -->
<div style="background: rgba(255, 255, 255, 0.95); 
             border-bottom: 1px solid var(--color-border-warm);
             box-shadow: var(--shadow-warm);">

<!-- Content Card -->
<div class="card card-warm">
  <h3 class="gradient-text">Title</h3>
  <p>Content here</p>
  <button class="btn btn-primary">Action</button>
</div>

<!-- Form Group -->
<div style="margin-bottom: var(--space-lg);">
  <label style="color: var(--color-text-medium);">Label</label>
  <input class="input" placeholder="Enter...">
</div>

<!-- Status Badge -->
<span class="badge badge-success">✓ Complete</span>
```

## File Quick Access

| What You Need | File to Open |
|---------------|-------------|
| See examples | `design-demo.html` |
| Full specs | `DESIGN_SYSTEM.md` |
| How to integrate | `THEME_UPDATE_SUMMARY.md` |
| Convert pages | `QUICK_CONVERSION_GUIDE.md` |
| Quick start | `FRONTEND_README.md` |
| Compare themes | `THEME_COMPARISON.md` |

## Three-Step Integration

1. **Add CSS**: `<link rel="stylesheet" href="summer-theme.css">`
2. **Update body**: `background: var(--gradient-bg); color: var(--color-text-dark);`
3. **Use classes**: Replace inline styles with utility classes

## Most Used Classes

```
.btn .btn-primary     → Primary button
.btn .btn-secondary   → Secondary button
.card                 → White card
.card .card-warm      → Highlighted card
.input                → Form input
.badge .badge-success → Success badge
.gradient-text        → Gradient heading
.text-medium          → Secondary text
```

## Key Variables

```
var(--color-coral)        → #FF6B6B
var(--color-teal)         → #4ECDC4
var(--color-text-dark)    → #2C3E50
var(--color-bg-white)     → #FFFFFF
var(--gradient-bg)        → Page background
var(--space-lg)           → 24px spacing
var(--radius-md)          → 12px border
var(--shadow-md)          → Medium shadow
```

## Remember

✅ Light backgrounds, dark text  
✅ Warm colors for primary actions  
✅ Cool colors for secondary actions  
✅ Generous white space  
✅ Subtle shadows  
✅ Smooth transitions  

---

**Made with ☀️**
