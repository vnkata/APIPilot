import { alpha, useTheme } from '@mui/material/styles'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { getStatusCodeToken } from '../../shared/ui/semanticBadgeUtils'

export type StatusChartDatum = {
  count: number
  status: string
}

type StatusBarChartProps = {
  data: StatusChartDatum[]
}

function Chart({ data, height, width }: StatusBarChartProps & { height: number; width: number }) {
  const theme = useTheme()

  return (
    <BarChart data={data} height={height} width={width}>
      <CartesianGrid stroke={theme.apiTesting.border.subtle} strokeDasharray="3 3" />
      <XAxis
        dataKey="status"
        stroke={theme.palette.text.secondary}
        tick={{ fill: theme.palette.text.secondary, fontSize: 12 }}
      />
      <YAxis
        allowDecimals={false}
        stroke={theme.palette.text.secondary}
        tick={{ fill: theme.palette.text.secondary, fontSize: 12 }}
      />
      <Tooltip
        contentStyle={{
          background: theme.apiTesting.surface.elevated,
          border: `1px solid ${theme.apiTesting.border.default}`,
          borderRadius: 8,
          color: theme.palette.text.primary,
        }}
        cursor={{ fill: alpha(theme.palette.primary.main, 0.08) }}
      />
      <Bar dataKey="count" radius={[4, 4, 0, 0]}>
        {data.map((datum) => {
          const token = theme.apiTesting.statusCode[getStatusCodeToken(datum.status)]
          return <Cell fill={token.fg} key={datum.status} />
        })}
      </Bar>
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
