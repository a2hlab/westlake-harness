import fs from '@ohos.file.fs';
import { Want } from '@kit.AbilityKit';
import { hilog } from '@kit.PerformanceAnalysisKit';

const DOMAIN = 0x0000;
const TAG = 'ConfirmPage';
const BASE_DIR = '/data/local/tmp/aonb_confirm';

function formatUtcTimestamp(d: Date): string {
  // 2026-07-25T12:00:00Z
  return d.toISOString().replace(/\.\d{3}Z$/, 'Z');
}

function defaultRunId(): string {
  const d = new Date();
  const pad = (n: number): string => String(n).padStart(2, '0');
  const y = d.getUTCFullYear();
  const m = pad(d.getUTCMonth() + 1);
  const day = pad(d.getUTCDate());
  const h = pad(d.getUTCHours());
  const min = pad(d.getUTCMinutes());
  const s = pad(d.getUTCSeconds());
  return `${y}${m}${day}T${h}${min}${s}Z`;
}

function ensureDir(path: string): void {
  const parts = path.split('/').filter(p => p.length > 0);
  let current = '';
  for (const part of parts) {
    current += '/' + part;
    if (!fs.access(current)) {
      fs.mkdir(current);
    }
  }
}

@Entry
@Component
struct Index {
  @State actionId: string = '';
  @State caseId: string = '';
  @State summary: string = '';
  @State runId: string = '';
  @State deviceSerial: string = '';
  @State status: string = '';
  @State confirmed: boolean = false;

  aboutToAppear() {
    const want: Want | undefined = AppStorage.get<Want>('confirmWant');
    this.actionId = this.extractString(want?.parameters?.['action']);
    this.caseId = this.extractString(want?.parameters?.['case']);
    this.summary = this.extractString(want?.parameters?.['summary']);
    this.runId = this.extractString(want?.parameters?.['runId']) || defaultRunId();
    this.deviceSerial = this.extractString(want?.parameters?.['serial']) || 'unknown';
    hilog.info(DOMAIN, TAG, 'parsed action=%{public}s case=%{public}s runId=%{public}s',
      this.actionId, this.caseId, this.runId);
  }

  private extractString(value: string | Object | undefined): string {
    if (value === undefined || value === null) {
      return '';
    }
    if (typeof value === 'string') {
      return value;
    }
    return String(value);
  }

  private buildYamlContent(): string {
    return [
      `confirmed_at_utc: ${formatUtcTimestamp(new Date())}`,
      `action_id: ${this.actionId}`,
      `case_id: ${this.caseId}`,
      `device_serial: ${this.deviceSerial}`,
      `run_id: ${this.runId}`,
      `confirmed_by: human_button_press`,
      ''
    ].join('\n');
  }

  private onConfirm() {
    if (this.confirmed) {
      return;
    }
    if (!this.actionId || !this.caseId) {
      this.status = '缺少 action 或 case 参数';
      hilog.error(DOMAIN, TAG, 'Missing action or case parameter');
      return;
    }

    const dir = `${BASE_DIR}/${this.runId}/${this.actionId}`;
    const filePath = `${dir}/${this.caseId}.confirmed`;
    const content = this.buildYamlContent();

    try {
      ensureDir(dir);
      const file = fs.openSync(filePath, fs.OpenMode.READ_WRITE | fs.OpenMode.CREATE);
      fs.truncateSync(file.fd);
      fs.writeSync(file.fd, content);
      fs.closeSync(file);
      this.status = `已写入: ${filePath}`;
      this.confirmed = true;
      hilog.info(DOMAIN, TAG, 'Confirmation written to %{public}s', filePath);
    } catch (e) {
      const msg = (e as Error).message || String(e);
      this.status = `写入失败: ${msg}`;
      hilog.error(DOMAIN, TAG, 'Failed to write confirmation: %{public}s', msg);
    }
  }

  build() {
    Column() {
      Text($r('app.string.page_title'))
        .fontSize(28)
        .fontWeight(FontWeight.Bold)
        .margin({ top: 40, bottom: 24 })

      Column() {
        Row() {
          Text($r('app.string.action_label'))
            .fontSize(18)
            .fontWeight(FontWeight.Medium)
            .width('120vp')
          Text(this.actionId || '-')
            .fontSize(18)
            .layoutWeight(1)
        }
        .width('100%')
        .margin(8)

        Row() {
          Text($r('app.string.case_label'))
            .fontSize(18)
            .fontWeight(FontWeight.Medium)
            .width('120vp')
          Text(this.caseId || '-')
            .fontSize(18)
            .layoutWeight(1)
        }
        .width('100%')
        .margin(8)

        Row() {
          Text($r('app.string.summary_label'))
            .fontSize(18)
            .fontWeight(FontWeight.Medium)
            .width('120vp')
          Text(this.summary || '-')
            .fontSize(16)
            .layoutWeight(1)
            .maxLines(4)
            .textOverflow({ overflow: TextOverflow.Ellipsis })
        }
        .width('100%')
        .margin(8)

        Row() {
          Text('Run ID:')
            .fontSize(14)
            .fontColor('#666666')
            .width('80vp')
          Text(this.runId || '-')
            .fontSize(14)
            .fontColor('#666666')
            .layoutWeight(1)
            .maxLines(1)
            .textOverflow({ overflow: TextOverflow.Ellipsis })
        }
        .width('100%')
        .margin(8)
      }
      .width('90%')
      .padding(16)
      .backgroundColor('#F5F5F5')
      .borderRadius(12)
      .margin({ bottom: 40 })

      if (!this.confirmed) {
        Button($r('app.string.confirm_button'), { type: ButtonType.Capsule, stateEffect: true })
          .width('80%')
          .height(60)
          .fontSize(24)
          .backgroundColor($r('app.color.primary'))
          .onClick(() => this.onConfirm())
      } else {
        Text($r('app.string.confirmed_label'))
          .fontSize(26)
          .fontColor($r('app.color.success'))
          .margin(20)
      }

      if (this.status !== '') {
        Text(this.status)
          .fontSize(14)
          .fontColor(this.confirmed ? $r('app.color.success') : $r('app.color.error'))
          .margin(20)
          .maxLines(4)
          .textOverflow({ overflow: TextOverflow.Ellipsis })
      }
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#FFFFFF')
    .justifyContent(FlexAlign.Center)
    .alignItems(HorizontalAlign.Center)
  }
}
