import { DialogModule, DialogRef, DIALOG_DATA } from '@angular/cdk/dialog';
import { NgModule } from '@angular/core';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { RouterTestingModule } from '@angular/router/testing';
import { ToastrService } from 'ngx-toastr';


@NgModule({
  imports: [
    HttpClientTestingModule,
    RouterTestingModule,
    FormsModule,
    ReactiveFormsModule,
    DialogModule,
    NoopAnimationsModule,
  ],
  exports: [
    HttpClientTestingModule,
    RouterTestingModule,
    FormsModule,
    ReactiveFormsModule,
    DialogModule,
    NoopAnimationsModule,
  ],
  providers: [
    { provide: DIALOG_DATA, useValue: {} },
    { provide: DialogRef, useValue: { close: jasmine.createSpy('close') } },
    {
      provide: ToastrService,
      useValue: {
        success: jasmine.createSpy('success'),
        error: jasmine.createSpy('error'),
        warning: jasmine.createSpy('warning'),
        info: jasmine.createSpy('info'),
      },
    },
  ],
})
export class SkillBridgeTestingModule {}
