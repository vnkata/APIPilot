import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

export type StatusChartDatum = {
  count: number
  status: string
}

type StatusBarChartProps = {
  data: StatusChartDatum[]
}

function Chart({ data, height, width }: StatusBarChartProps & { height: number; width: number }) {
  return (
    <BarChart data={data} height={height} width={width}>
      <CartesianGrid strokeDasharray="3 3" />
      <XAxis dataKey="status" />
      <YAxis allowDecimals={false} />
      <Tooltip />
      <Bar dataKey="count" fill="#1f6feb" radius={[4, 4, 0, 0]} />
    </BarChart>
  )
}

export function StatusBarChart({ data }: StatusBarChartProps) {
  if (import.meta.env.MODE === 'test') {
    return <Chart data={data} height={240} width={640} />
  }

  return (
    <ResponsiveContainer height={240} width="100%">
      <Chart data={data} height={240} width={640} />
    </ResponsiveContainer>
  )
}
