import { ComponentFixture, TestBed } from '@angular/core/testing';

import { BookServiceComponent } from './book-service.component';
import { SkillBridgeTestingModule } from '../../../../testing/skillbridge-testing.module';
import { DIALOG_DATA } from '@angular/cdk/dialog';

describe('BookServiceComponent', () => {
  let component: BookServiceComponent;
  let fixture: ComponentFixture<BookServiceComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [BookServiceComponent],
      imports: [SkillBridgeTestingModule],
      providers: [{
        provide: DIALOG_DATA,
        useValue: {
          service_name: 'Test service',
          tutor: { full_name: 'Test Tutor', email: 'tutor@hs-fulda.de', is_verified: true },
          price: 20,
          description: 'Test description',
          date: '2026-09-20',
          time: '10:00:00',
          end_time: '11:00:00',
          level: 'BEGINNER'
        }
      }]
    });
    fixture = TestBed.createComponent(BookServiceComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
