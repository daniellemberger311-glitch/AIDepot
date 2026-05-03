interface Props { title: React.ReactNode; subtitle?: string; action?: React.ReactNode }

export default function PageHeader({ title, subtitle, action }: Props) {
  return (
    <div className="flex items-center justify-between px-6 py-5 border-b border-gray-800">
      <div>
        <h1 className="text-xl font-semibold text-white">{title}</h1>
        {subtitle && <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>}
      </div>
      {action && <div>{action}</div>}
    </div>
  )
}
