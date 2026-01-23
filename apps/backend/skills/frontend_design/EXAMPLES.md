# Frontend Design Examples

This document provides before/after comparisons demonstrating the Professional Frontend Design skill standards.

---

## 1. Button Component

### Before: Generic Implementation

```tsx
// Generic, unstyled button
function Button({ children, onClick, disabled }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        padding: '8px 16px',
        backgroundColor: '#007bff',
        color: 'white',
        border: 'none',
        borderRadius: '4px',
        cursor: disabled ? 'not-allowed' : 'pointer',
      }}
    >
      {children}
    </button>
  );
}
```

**Issues:**
- Inline styles (unmaintainable)
- No accessibility considerations
- No focus states
- No variants or sizes
- Generic blue color

### After: Professional Implementation

```tsx
import { forwardRef, type ButtonHTMLAttributes } from 'react';
import { cn } from '@/lib/utils';
import { Loader2 } from 'lucide-react';

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

const variantStyles: Record<ButtonVariant, string> = {
  primary: cn(
    'bg-primary text-primary-foreground',
    'hover:bg-primary/90',
    'active:bg-primary/80',
    'shadow-sm hover:shadow-md'
  ),
  secondary: cn(
    'bg-secondary text-secondary-foreground',
    'hover:bg-secondary/80',
    'border border-border'
  ),
  ghost: cn(
    'bg-transparent',
    'hover:bg-muted',
    'text-foreground'
  ),
  danger: cn(
    'bg-danger text-white',
    'hover:bg-danger/90',
    'active:bg-danger/80'
  ),
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: 'h-8 px-3 text-xs gap-1.5',
  md: 'h-10 px-4 text-sm gap-2',
  lg: 'h-12 px-6 text-base gap-2.5',
};

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = 'primary',
      size = 'md',
      isLoading = false,
      leftIcon,
      rightIcon,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const isDisabled = disabled || isLoading;

    return (
      <button
        ref={ref}
        disabled={isDisabled}
        className={cn(
          // Base styles
          'inline-flex items-center justify-center',
          'font-medium rounded-lg',
          'transition-all duration-200 ease-out',
          // Focus styles (accessibility)
          'focus-visible:outline-none focus-visible:ring-2',
          'focus-visible:ring-ring focus-visible:ring-offset-2',
          // Disabled styles
          'disabled:opacity-50 disabled:cursor-not-allowed',
          'disabled:pointer-events-none',
          // Variant and size
          variantStyles[variant],
          sizeStyles[size],
          className
        )}
        {...props}
      >
        {isLoading ? (
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
        ) : (
          leftIcon
        )}
        <span>{children}</span>
        {!isLoading && rightIcon}
      </button>
    );
  }
);

Button.displayName = 'Button';

export { Button, type ButtonProps, type ButtonVariant, type ButtonSize };
```

**Improvements:**
- Fully typed with TypeScript
- Multiple variants and sizes
- Proper focus indicators (accessibility)
- Loading state with spinner
- Icon support
- forwardRef for ref passing
- Semantic disabled state
- Smooth transitions
- Design system tokens

---

## 2. Card Component

### Before: Generic Card

```tsx
function Card({ title, description, image }) {
  return (
    <div style={{
      border: '1px solid #ddd',
      borderRadius: '8px',
      padding: '16px',
      backgroundColor: 'white',
    }}>
      <img src={image} alt="" style={{ width: '100%' }} />
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  );
}
```

### After: Professional Card

```tsx
import { cn } from '@/lib/utils';
import { type ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
  variant?: 'default' | 'elevated' | 'outlined' | 'interactive';
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

const variantStyles = {
  default: 'bg-card border border-border/50',
  elevated: 'bg-card shadow-lg shadow-black/5',
  outlined: 'bg-transparent border-2 border-border',
  interactive: cn(
    'bg-card border border-border/50',
    'hover:border-border hover:shadow-md',
    'cursor-pointer transition-all duration-200',
    'active:scale-[0.98]'
  ),
};

const paddingStyles = {
  none: 'p-0',
  sm: 'p-4',
  md: 'p-6',
  lg: 'p-8',
};

function Card({
  children,
  className,
  variant = 'default',
  padding = 'md',
}: CardProps) {
  return (
    <div
      className={cn(
        'rounded-xl overflow-hidden',
        variantStyles[variant],
        paddingStyles[padding],
        className
      )}
    >
      {children}
    </div>
  );
}

function CardHeader({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn('space-y-1.5', className)}>
      {children}
    </div>
  );
}

function CardTitle({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <h3 className={cn(
      'text-lg font-semibold leading-tight tracking-tight',
      'text-foreground',
      className
    )}>
      {children}
    </h3>
  );
}

function CardDescription({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <p className={cn('text-sm text-muted-foreground', className)}>
      {children}
    </p>
  );
}

function CardContent({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn('pt-4', className)}>
      {children}
    </div>
  );
}

function CardFooter({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn('flex items-center pt-4', className)}>
      {children}
    </div>
  );
}

function CardImage({
  src,
  alt,
  className,
  aspectRatio = '16/9',
}: {
  src: string;
  alt: string;
  className?: string;
  aspectRatio?: string;
}) {
  return (
    <div
      className={cn('relative overflow-hidden bg-muted', className)}
      style={{ aspectRatio }}
    >
      <img
        src={src}
        alt={alt}
        loading="lazy"
        className="absolute inset-0 h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
      />
    </div>
  );
}

export {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
  CardImage,
};
```

**Usage Example:**

```tsx
<Card variant="interactive" padding="none" className="group">
  <CardImage
    src="/product.jpg"
    alt="Product showcase"
    aspectRatio="4/3"
  />
  <div className="p-6">
    <CardHeader>
      <CardTitle>Premium Headphones</CardTitle>
      <CardDescription>Immersive sound experience</CardDescription>
    </CardHeader>
    <CardContent>
      <p className="text-2xl font-bold">$299</p>
    </CardContent>
    <CardFooter>
      <Button size="sm" className="w-full">Add to Cart</Button>
    </CardFooter>
  </div>
</Card>
```

---

## 3. Form Input

### Before: Basic Input

```tsx
function Input({ label, error, ...props }) {
  return (
    <div>
      <label>{label}</label>
      <input
        {...props}
        style={{
          width: '100%',
          padding: '8px',
          border: error ? '1px solid red' : '1px solid #ccc',
          borderRadius: '4px',
        }}
      />
      {error && <span style={{ color: 'red' }}>{error}</span>}
    </div>
  );
}
```

### After: Professional Form Input

```tsx
import { forwardRef, type InputHTMLAttributes, useId } from 'react';
import { cn } from '@/lib/utils';
import { AlertCircle, Check } from 'lucide-react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  description?: string;
  error?: string;
  success?: boolean;
  leftAddon?: React.ReactNode;
  rightAddon?: React.ReactNode;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      className,
      label,
      description,
      error,
      success,
      leftAddon,
      rightAddon,
      disabled,
      required,
      id: providedId,
      ...props
    },
    ref
  ) => {
    const generatedId = useId();
    const id = providedId || generatedId;
    const descriptionId = `${id}-description`;
    const errorId = `${id}-error`;

    const hasError = Boolean(error);
    const hasDescription = Boolean(description);

    return (
      <div className="w-full space-y-2">
        {label && (
          <label
            htmlFor={id}
            className={cn(
              'block text-sm font-medium',
              hasError ? 'text-danger' : 'text-foreground'
            )}
          >
            {label}
            {required && (
              <span className="text-danger ml-1" aria-hidden="true">*</span>
            )}
          </label>
        )}

        {description && !hasError && (
          <p
            id={descriptionId}
            className="text-sm text-muted-foreground"
          >
            {description}
          </p>
        )}

        <div className="relative">
          {leftAddon && (
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
              {leftAddon}
            </div>
          )}

          <input
            ref={ref}
            id={id}
            disabled={disabled}
            aria-invalid={hasError}
            aria-describedby={cn(
              hasDescription && !hasError && descriptionId,
              hasError && errorId
            ) || undefined}
            className={cn(
              // Base styles
              'w-full rounded-lg border bg-background px-4 py-2.5',
              'text-sm text-foreground placeholder:text-muted-foreground',
              // Transitions
              'transition-all duration-200',
              // Focus styles
              'focus:outline-none focus:ring-2 focus:ring-offset-0',
              // Default state
              !hasError && !success && [
                'border-border',
                'focus:border-primary focus:ring-primary/20',
                'hover:border-border-hover',
              ],
              // Error state
              hasError && [
                'border-danger',
                'focus:border-danger focus:ring-danger/20',
                'text-danger',
              ],
              // Success state
              success && !hasError && [
                'border-success',
                'focus:border-success focus:ring-success/20',
              ],
              // Disabled state
              disabled && 'opacity-50 cursor-not-allowed bg-muted',
              // Addons padding
              leftAddon && 'pl-10',
              rightAddon && 'pr-10',
              className
            )}
            {...props}
          />

          {(rightAddon || hasError || success) && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2">
              {hasError ? (
                <AlertCircle className="h-4 w-4 text-danger" aria-hidden="true" />
              ) : success ? (
                <Check className="h-4 w-4 text-success" aria-hidden="true" />
              ) : (
                rightAddon
              )}
            </div>
          )}
        </div>

        {hasError && (
          <p
            id={errorId}
            role="alert"
            className="flex items-center gap-1.5 text-sm text-danger"
          >
            <AlertCircle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            {error}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

export { Input, type InputProps };
```

**Usage Example:**

```tsx
<form className="space-y-6">
  <Input
    label="Email Address"
    type="email"
    placeholder="you@example.com"
    description="We'll never share your email."
    required
    leftAddon={<Mail className="h-4 w-4" />}
  />

  <Input
    label="Password"
    type="password"
    placeholder="Enter your password"
    error="Password must be at least 8 characters"
    required
  />

  <Input
    label="Username"
    placeholder="Choose a username"
    success
    rightAddon={<Check className="h-4 w-4 text-success" />}
  />
</form>
```

---

## 4. Modal / Dialog

### Before: Basic Modal

```tsx
function Modal({ isOpen, onClose, children }) {
  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
    }}>
      <div style={{
        backgroundColor: 'white',
        padding: '20px',
        borderRadius: '8px',
      }}>
        <button onClick={onClose}>X</button>
        {children}
      </div>
    </div>
  );
}
```

### After: Accessible Dialog

```tsx
import { Fragment, useEffect, useRef, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { cn } from '@/lib/utils';
import { X } from 'lucide-react';

interface DialogProps {
  isOpen: boolean;
  onClose: () => void;
  children: ReactNode;
  title: string;
  description?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
}

const sizeStyles = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-xl',
  full: 'max-w-[calc(100vw-2rem)] max-h-[calc(100vh-2rem)]',
};

function Dialog({
  isOpen,
  onClose,
  children,
  title,
  description,
  size = 'md',
}: DialogProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const previousActiveElement = useRef<HTMLElement | null>(null);

  // Handle escape key
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    }

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Focus management
  useEffect(() => {
    if (isOpen) {
      previousActiveElement.current = document.activeElement as HTMLElement;
      dialogRef.current?.focus();

      // Lock body scroll
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
      previousActiveElement.current?.focus();
    }

    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  // Focus trap
  useEffect(() => {
    if (!isOpen) return;

    function handleTabKey(e: KeyboardEvent) {
      if (e.key !== 'Tab' || !dialogRef.current) return;

      const focusableElements = dialogRef.current.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];

      if (e.shiftKey && document.activeElement === firstElement) {
        e.preventDefault();
        lastElement?.focus();
      } else if (!e.shiftKey && document.activeElement === lastElement) {
        e.preventDefault();
        firstElement?.focus();
      }
    }

    document.addEventListener('keydown', handleTabKey);
    return () => document.removeEventListener('keydown', handleTabKey);
  }, [isOpen]);

  if (!isOpen) return null;

  return createPortal(
    <Fragment>
      {/* Backdrop */}
      <div
        className={cn(
          'fixed inset-0 z-50',
          'bg-black/60 backdrop-blur-sm',
          'animate-in fade-in duration-200'
        )}
        aria-hidden="true"
        onClick={onClose}
      />

      {/* Dialog */}
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="dialog-title"
        aria-describedby={description ? 'dialog-description' : undefined}
        tabIndex={-1}
        className={cn(
          'fixed left-1/2 top-1/2 z-50',
          '-translate-x-1/2 -translate-y-1/2',
          'w-full',
          sizeStyles[size],
          // Appearance
          'bg-background rounded-xl shadow-2xl',
          'border border-border/50',
          // Animation
          'animate-in fade-in zoom-in-95 duration-200'
        )}
      >
        {/* Header */}
        <div className="flex items-start justify-between p-6 pb-0">
          <div className="space-y-1.5 pr-8">
            <h2
              id="dialog-title"
              className="text-lg font-semibold leading-tight"
            >
              {title}
            </h2>
            {description && (
              <p
                id="dialog-description"
                className="text-sm text-muted-foreground"
              >
                {description}
              </p>
            )}
          </div>

          <button
            onClick={onClose}
            className={cn(
              'absolute right-4 top-4',
              'rounded-lg p-2',
              'text-muted-foreground hover:text-foreground',
              'hover:bg-muted',
              'transition-colors duration-150',
              'focus-visible:outline-none focus-visible:ring-2',
              'focus-visible:ring-ring'
            )}
            aria-label="Close dialog"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {children}
        </div>
      </div>
    </Fragment>,
    document.body
  );
}

function DialogFooter({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        'flex flex-col-reverse gap-2',
        'sm:flex-row sm:justify-end',
        'pt-4 border-t border-border/50 mt-2',
        className
      )}
    >
      {children}
    </div>
  );
}

export { Dialog, DialogFooter };
```

---

## 5. Navigation / Navbar

### Before: Basic Navigation

```tsx
function Navbar() {
  return (
    <nav style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 20px' }}>
      <div>Logo</div>
      <ul style={{ display: 'flex', listStyle: 'none', gap: '20px' }}>
        <li><a href="/">Home</a></li>
        <li><a href="/about">About</a></li>
        <li><a href="/contact">Contact</a></li>
      </ul>
    </nav>
  );
}
```

### After: Professional Navigation

```tsx
import { useState } from 'react';
import { cn } from '@/lib/utils';
import { Menu, X } from 'lucide-react';

interface NavItem {
  label: string;
  href: string;
  isActive?: boolean;
}

interface NavbarProps {
  logo: React.ReactNode;
  items: NavItem[];
  actions?: React.ReactNode;
}

function Navbar({ logo, items, actions }: NavbarProps) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  return (
    <header
      className={cn(
        'sticky top-0 z-40',
        'bg-background/80 backdrop-blur-lg',
        'border-b border-border/50'
      )}
    >
      <nav
        className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8"
        aria-label="Main navigation"
      >
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <div className="flex-shrink-0">
            <a
              href="/"
              className="flex items-center gap-2 font-bold text-xl"
              aria-label="Home"
            >
              {logo}
            </a>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex md:items-center md:gap-1">
            {items.map((item) => (
              <a
                key={item.href}
                href={item.href}
                className={cn(
                  'px-4 py-2 rounded-lg',
                  'text-sm font-medium',
                  'transition-colors duration-150',
                  item.isActive
                    ? 'bg-primary/10 text-primary'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                )}
                aria-current={item.isActive ? 'page' : undefined}
              >
                {item.label}
              </a>
            ))}
          </div>

          {/* Actions */}
          <div className="hidden md:flex md:items-center md:gap-4">
            {actions}
          </div>

          {/* Mobile menu button */}
          <button
            type="button"
            className={cn(
              'md:hidden',
              'p-2 rounded-lg',
              'text-muted-foreground hover:text-foreground',
              'hover:bg-muted',
              'transition-colors duration-150',
              'focus-visible:outline-none focus-visible:ring-2',
              'focus-visible:ring-ring'
            )}
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            aria-expanded={isMobileMenuOpen}
            aria-controls="mobile-menu"
            aria-label={isMobileMenuOpen ? 'Close menu' : 'Open menu'}
          >
            {isMobileMenuOpen ? (
              <X className="h-6 w-6" aria-hidden="true" />
            ) : (
              <Menu className="h-6 w-6" aria-hidden="true" />
            )}
          </button>
        </div>

        {/* Mobile menu */}
        <div
          id="mobile-menu"
          className={cn(
            'md:hidden',
            'overflow-hidden transition-all duration-300 ease-out',
            isMobileMenuOpen ? 'max-h-96 pb-4' : 'max-h-0'
          )}
        >
          <div className="space-y-1 pt-2">
            {items.map((item) => (
              <a
                key={item.href}
                href={item.href}
                className={cn(
                  'block px-4 py-3 rounded-lg',
                  'text-base font-medium',
                  'transition-colors duration-150',
                  item.isActive
                    ? 'bg-primary/10 text-primary'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                )}
                aria-current={item.isActive ? 'page' : undefined}
              >
                {item.label}
              </a>
            ))}

            {actions && (
              <div className="pt-4 px-4 space-y-2 border-t border-border/50 mt-2">
                {actions}
              </div>
            )}
          </div>
        </div>
      </nav>
    </header>
  );
}

export { Navbar, type NavItem, type NavbarProps };
```

---

## Summary of Improvements

| Aspect | Before | After |
|--------|--------|-------|
| **Styling** | Inline styles | Tailwind utilities with design tokens |
| **Accessibility** | Missing | Full ARIA, focus management, keyboard nav |
| **TypeScript** | Weak or none | Fully typed with proper interfaces |
| **Variants** | Single style | Multiple configurable variants |
| **Responsiveness** | None | Mobile-first responsive design |
| **Animation** | None | Smooth, purposeful transitions |
| **Documentation** | None | Self-documenting with types |
| **Reusability** | Low | High, composable architecture |

---

*Frontend Design Examples - Claude God Code*
