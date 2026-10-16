import { NgModule , CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ServiceRequestsComponent } from './service-requests/service-requests.component';
import { TutorRoutingModule } from './tutor-routing.module';
import { MyProfileComponent } from './my-profile/my-profile.component';
import { TutorDashboardComponent } from './tutor-dashboard/tutor-dashboard.component';
import { TutorComponent } from './tutor.component';
import { HttpClientModule } from '@angular/common/http';
import { ReactiveFormsModule } from '@angular/forms';
import { TutorChatComponent } from './tutor-chat/tutor-chat.component';
import { ImageCropperComponent, ImageCropperModule } from 'ngx-image-cropper';
import { ServiceDashboardComponent } from './service-dashboard/service-dashboard.component';
import { TutorServicesComponent } from './services/tutor-services.component';
import { ServiceDetailsComponent } from './services/service-details.component';
import { ResourcesModule } from '../resources/resources.module';

@NgModule({
  declarations: [
    MyProfileComponent,
    TutorDashboardComponent,
    TutorComponent,
    TutorChatComponent,
    ServiceDashboardComponent,
    TutorServicesComponent,
    ServiceDetailsComponent,
    ServiceRequestsComponent,
  ],
  imports: [
    CommonModule,
    TutorRoutingModule,
    HttpClientModule,
    ReactiveFormsModule,
    ImageCropperModule,
    ResourcesModule
  ],
  schemas: [CUSTOM_ELEMENTS_SCHEMA]
})
export class TutorModule { }
