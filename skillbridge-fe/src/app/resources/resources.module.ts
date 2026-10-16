import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NotificationTrayComponent } from './notification-tray/notification-tray.component';
import { DismissableMenuDirective } from './directives/dismissable-menu.directive';

@NgModule({
  declarations: [NotificationTrayComponent, DismissableMenuDirective],
  imports: [CommonModule],
  exports: [NotificationTrayComponent, DismissableMenuDirective]
})
export class ResourcesModule {}