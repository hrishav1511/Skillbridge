import { NgModule, CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClientModule } from '@angular/common/http';

import { StudentRoutingModule } from './student-routing.module';
import { DashboardComponent } from './dashboard/dashboard.component';
import { TutorListComponent } from './dashboard/tutor-list/tutor-list.component';
import { ServiceListComponent } from './dashboard/service-list/service-list.component';
import { ChatListComponent } from './chat-list/chat-list.component';
import { StudentComponent } from './student/student.component';
import { ViewTutorComponent } from './view-tutor/view-tutor.component';
import { ServicesListComponent } from './services-list/services-list.component';
import { PaymentPortalComponent } from './payment-portal/payment-portal.component';
import { FormsModule } from '@angular/forms';
import { CancelBookingComponent } from '../resources/Modals/cancel-booking/cancel-booking.component';
import { ResourcesModule } from '../resources/resources.module';


@NgModule({
  declarations: [
    DashboardComponent,
    TutorListComponent,
    ServiceListComponent,
    ChatListComponent,
    StudentComponent,
    ViewTutorComponent,
    ServicesListComponent,
    PaymentPortalComponent,
    CancelBookingComponent
  ],
  imports: [
    CommonModule,
    HttpClientModule,
      FormsModule,
    StudentRoutingModule,
    ResourcesModule,
    CommonModule,
  ],
  exports: [ChatListComponent],
  schemas: [CUSTOM_ELEMENTS_SCHEMA]
})
export class StudentModule { }
