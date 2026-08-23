import { DevicesPanel } from '../components/DevicesPanel'

export function DevicesPage() {
  return <div className="page-stack"><header className="page-header"><p className="eyebrow">Profile settings</p><h1>Devices</h1><p className="muted">A NutriBox device is optional and can be connected when available.</p></header><DevicesPanel /></div>
}
