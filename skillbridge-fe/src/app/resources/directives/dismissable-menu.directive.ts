import { Directive, ElementRef, HostListener, Input } from '@angular/core';

/**
 * Closes a checkbox-toggled dropdown on an outside click or Escape.
 *
 * The notification and profile menus are opened with the CSS checkbox pattern
 * (a hidden `<input type="checkbox">` plus a `<label>`, with the tray revealed
 * by a `:checked ~ ...` rule). That has no JavaScript state, so nothing was
 * listening for a click elsewhere on the page and the only way to close a menu
 * was to hit its toggle again.
 *
 * Rather than convert every menu to component state, this unchecks the inner
 * toggle, which leaves the existing markup and CSS exactly as they are.
 *
 * Usage: `<div class="notification-menu" appDismissableMenu>`
 */
@Directive({
  selector: '[appDismissableMenu]'
})
export class DismissableMenuDirective {
  /** Selector for the checkbox that controls the menu. */
  @Input() appDismissableMenu = 'input[type="checkbox"]';

  constructor(private elementRef: ElementRef<HTMLElement>) {}

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    const target = event.target as Node | null;
    if (target && this.elementRef.nativeElement.contains(target)) {
      return;
    }
    this.close();
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    this.close();
  }

  private close(): void {
    const selector = this.appDismissableMenu || 'input[type="checkbox"]';
    const toggle = this.elementRef.nativeElement.querySelector<HTMLInputElement>(selector);
    if (toggle && toggle.checked) {
      toggle.checked = false;
    }
  }
}
