import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';

import { LayoutRoutingModule } from './layout-routing.module';
import { LayoutComponent } from './layout.component';
import { SidepanelComponent } from './sidepanel/sidepanel.component';
import { TopbarComponent } from './topbar/topbar.component';
import { ServiceApprovalComponent } from './service-approval/service-approval.component';
import { DashboardComponent } from './dashboard/dashboard.component';
import { UserApprovalComponent } from './user-approval/user-approval.component';
import { TutorVisibilityComponent } from './tutor-visibility/tutor-visibility.component';
import { AdminChatComponent } from './admin-chat/admin-chat.component';
import { FormsModule } from '@angular/forms';
import { ReportsComponent } from './reports/reports.component';
import { ServicesListComponent } from './services-list/services-list.component';
import { TutorsListComponent } from './tutors-list/tutors-list.component';
import { RecordDialogComponent } from './record-dialog/record-dialog.component';
import { DialogModule } from '@angular/cdk/dialog';


@NgModule({
  declarations: [
    LayoutComponent,
    SidepanelComponent,
    TopbarComponent,
    ServiceApprovalComponent,
    DashboardComponent,
    UserApprovalComponent,
    TutorVisibilityComponent,
    AdminChatComponent,
    ReportsComponent,
    ServicesListComponent,
    TutorsListComponent,
    RecordDialogComponent
  ],
  imports: [
    CommonModule,
    LayoutRoutingModule,
    FormsModule,
    DialogModule
  ]
})
export class LayoutModule { }
