import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AttachmenttsComponent } from './attachmentts.component';
import { SkillBridgeTestingModule } from '../../../../testing/skillbridge-testing.module';
import { DIALOG_DATA } from '@angular/cdk/dialog';

describe('AttachmenttsComponent', () => {
  let component: AttachmenttsComponent;
  let fixture: ComponentFixture<AttachmenttsComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [AttachmenttsComponent],
      imports: [SkillBridgeTestingModule],
      providers: [{ provide: DIALOG_DATA, useValue: { service: { id: 'service-id' }, attachments: [] } }]
    });
    fixture = TestBed.createComponent(AttachmenttsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
