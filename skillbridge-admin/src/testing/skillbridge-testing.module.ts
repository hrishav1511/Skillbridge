import { DialogModule, DialogRef, DIALOG_DATA } from '@angular/cdk/dialog';
import { NgModule } from '@angular/core';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { RouterTestingModule } from '@angular/router/testing';


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
    { provide: DIALOG_DATA, useValue: { action: 'APPROVE', item: { id: 'item-id' } } },
    { provide: DialogRef, useValue: { close: jasmine.createSpy('close') } },
  ],
})
export class SkillBridgeTestingModule {}
