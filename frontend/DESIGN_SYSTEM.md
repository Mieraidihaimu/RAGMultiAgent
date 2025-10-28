# Perplexity-Inspired Summer Theme Design System

## Overview
This design system provides a clean, professional interface inspired by Perplexity with warm, cheerful summer vibes. It prioritizes clarity, minimalism, and a positive user experience.

## Color Palette

### Primary Colors (Summer Gradients)
- **Coral**: `#FF6B6B` - Energy, warmth, primary actions
- **Peach**: `#FF8E53` - Softer warmth, accents
- **Yellow**: `#FFC93C` - Sunshine, happiness, highlights
- **Gold**: `#FFD93D` - Bright accents

### Secondary Colors (Cool Summer)
- **Teal**: `#4ECDC4` - Calm, trust, secondary actions
- **Mint**: `#44A08D` - Fresh, growth
- **Sky**: `#5DADE2` - Open, friendly
- **Ocean**: `#3498DB` - Deep, reliable

### Neutrals
- **Text Dark**: `#2C3E50` - Primary text
- **Text Medium**: `#666` - Secondary text
- **Text Light**: `#999` - Tertiary text, placeholders
- **Background White**: `#FFFFFF` - Cards, containers
- **Background Light**: `#F8F9FA` - Page backgrounds
- **Background Warm**: `#FFF5E6` - Warm sections
- **Border**: `#E0E0E0` - Standard borders
- **Border Warm**: `rgba(255, 200, 124, 0.2)` - Accent borders

## Typography

### Font Stack
```css
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', sans-serif;
```

### Font Sizes
- **Hero**: `2.8rem` (700-800 weight)
- **H1**: `2.5rem` (700 weight)
- **H2**: `2rem` (600-700 weight)
- **H3**: `1.5rem` (600 weight)
- **Body**: `1rem` (400 weight)
- **Small**: `0.875rem` (400-500 weight)
- **Tiny**: `0.75rem` (400-600 weight)

### Gradients for Text
```css
/* Primary gradient */
background: linear-gradient(135deg, #2C3E50 0%, #FF6B6B 50%, #FFC93C 100%);
-webkit-background-clip: text;
-webkit-text-fill-color: transparent;
background-clip: text;

/* Warm gradient */
background: linear-gradient(135deg, #FF6B6B 0%, #FFC93C 100%);
```

## Layout

### Page Background
```css
background: linear-gradient(135deg, #FFF5E6 0%, #FFF9F0 50%, #F0F9FF 100%);
```

### Ambient Effects
```css
background: 
    radial-gradient(circle at 20% 20%, rgba(255, 200, 124, 0.08) 0%, transparent 50%),
    radial-gradient(circle at 80% 80%, rgba(78, 205, 196, 0.08) 0%, transparent 50%),
    radial-gradient(circle at 50% 50%, rgba(93, 173, 226, 0.05) 0%, transparent 50%);
```

## Components

### Buttons

#### Primary Button
```css
background: linear-gradient(135deg, #FF6B6B, #FFC93C);
color: white;
padding: 10px 20px;
border-radius: 12px;
box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
font-weight: 600;
```

Hover: `translateY(-2px)` + `box-shadow: 0 6px 20px rgba(255, 107, 107, 0.25)`

#### Secondary Button
```css
background: white;
border: 2px solid rgba(255, 200, 124, 0.25);
color: #666;
padding: 9px 16px;
border-radius: 10px;
box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
```

Hover: Background `rgba(255, 200, 124, 0.15)`, color `#FF6B6B`

### Cards

#### Standard Card
```css
background: rgba(255, 255, 255, 0.98);
border: 2px solid rgba(255, 200, 124, 0.2);
border-radius: 16px;
padding: 20px;
box-shadow: 0 8px 32px rgba(255, 142, 83, 0.1), 0 2px 8px rgba(0, 0, 0, 0.05);
```

Hover: `translateY(-2px)` + enhanced shadow

### Input Fields

```css
background: white;
border: 2px solid #E0E0E0;
border-radius: 12px;
padding: 12px 16px;
color: #2C3E50;
font-size: 0.95rem;
```

Focus: 
```css
border-color: #FF8E53;
box-shadow: 0 0 0 3px rgba(255, 142, 83, 0.1);
```

### Header/Navigation

```css
background: rgba(255, 255, 255, 0.95);
backdrop-filter: blur(20px);
border-bottom: 1px solid rgba(255, 200, 124, 0.15);
box-shadow: 0 2px 12px rgba(255, 139, 83, 0.08);
padding: 16px 28px;
```

### Badges/Tags

#### Status Badges
- **Success**: Teal background `rgba(78, 205, 196, 0.15)`, teal text
- **Warning**: Yellow background `rgba(255, 201, 60, 0.15)`, gold text
- **Info**: Sky background `rgba(93, 173, 226, 0.15)`, sky text
- **Primary**: Coral/Yellow background, coral text

```css
padding: 4px 12px;
border-radius: 20px;
font-size: 0.75rem;
font-weight: 700;
text-transform: uppercase;
border: 1px solid [matching-color];
```

## Spacing System

- **XS**: 0.5rem (8px)
- **SM**: 0.75rem (12px)
- **MD**: 1rem (16px)
- **LG**: 1.5rem (24px)
- **XL**: 2rem (32px)
- **2XL**: 3rem (48px)
- **3XL**: 4rem (64px)

## Border Radius

- **SM**: 8px - Small elements
- **MD**: 12px - Buttons, inputs
- **LG**: 16px - Cards
- **XL**: 20px - Large containers
- **Full**: 9999px - Pills, circular

## Shadows

### Light Shadows (Default)
```css
--shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.04);
--shadow-md: 0 4px 12px rgba(0, 0, 0, 0.08);
--shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.12);
```

### Warm Shadows (Accent)
```css
--shadow-warm: 0 8px 32px rgba(255, 142, 83, 0.1);
--shadow-coral: 0 6px 20px rgba(255, 107, 107, 0.25);
--shadow-teal: 0 6px 20px rgba(78, 205, 196, 0.25);
```

## Transitions

### Standard
```css
transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
```

### Smooth
```css
transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
```

## Animations

### Fade In
```css
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}
animation: fadeIn 0.4s ease;
```

### Float (for accent elements)
```css
@keyframes float {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-10px); }
}
animation: float 3s ease-in-out infinite;
```

## Best Practices

### Do's
✅ Use white/light backgrounds for main content
✅ Apply warm gradients for primary actions
✅ Use teal/cool colors for secondary actions
✅ Maintain high contrast for readability
✅ Use generous white space
✅ Keep shadows subtle
✅ Make interactive elements obvious (hover states)

### Don'ts
❌ Don't use dark backgrounds (unless for modals)
❌ Don't overuse gradients
❌ Don't use too many colors at once
❌ Don't use harsh shadows
❌ Don't sacrifice readability for style
❌ Don't ignore accessibility

## Accessibility

- **Minimum contrast**: 4.5:1 for normal text, 3:1 for large text
- **Focus indicators**: Always visible, 3px outline with 0.1 opacity background
- **Touch targets**: Minimum 44x44px
- **Motion**: Respect `prefers-reduced-motion`

## Implementation

### Quick Start
1. Add `summer-theme.css` to your HTML
2. Use CSS variables from `:root`
3. Apply utility classes for common patterns
4. Follow component guidelines for consistency

### Example Usage
```html
<button class="btn btn-primary">
    Submit Thought
</button>

<div class="card card-warm">
    <h3 class="gradient-text">Your Thoughts</h3>
    <p class="text-medium">Process your ideas</p>
</div>

<span class="badge badge-success">Completed</span>
```

## Migration from Dark Theme

1. Replace dark backgrounds with light
2. Change purple accents to coral/yellow
3. Update text colors from light to dark
4. Adjust shadows from heavy to light
5. Replace blue tones with warm tones
6. Test all interactive states

## Resources

- Color picker: Use `#FF6B6B`, `#FFC93C`, `#4ECDC4` as base
- Gradients: 135deg angle for consistency
- Shadows: rgba with low opacity (0.04-0.12)
- Border radius: Multiples of 4px
