import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { LayoutComponent } from './layout.component';
import { ServiceApprovalComponent } from './service-approval/service-approval.component';
import { DashboardComponent } from './dashboard/dashboard.component';
import { UserApprovalComponent } from './user-approval/user-approval.component';
import { TutorVisibilityComponent } from './tutor-visibility/tutor-visibility.component';
import { RoleGuard } from '../resources/guards/role.guard';
import { AdminChatComponent } from './admin-chat/admin-chat.component';
import { ReportsComponent } from './reports/reports.component';
import { ServicesListComponent } from './services-list/services-list.component';
import { TutorsListComponent } from './tutors-list/tutors-list.component';

export const routes: Routes = [
  {
    path: '',
    component: LayoutComponent,
    canActivate: [RoleGuard],
    data: { roles: ['ADMIN', 'SUPER_ADMIN'] },
    children: [
      {
        path: '',
        component: DashboardComponent
      },
      {
        path: 'service-approval',
        component: ServiceApprovalComponent
      },
      {
        path: 'tutor-approval',
        component: UserApprovalComponent
      },
      {
        path: 'tutor-visibility',
        component: TutorVisibilityComponent
      },
      {
        path: 'tutors',
        component: TutorsListComponent
      },
      {
        path: 'services',
        component: ServicesListComponent
      },
      {
        path: 'reports',
        component: ReportsComponent
      },
      {
        path: 'messages',
        component: AdminChatComponent
      }
    ]
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class LayoutRoutingModule { }
