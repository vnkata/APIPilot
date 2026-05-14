import { Card, CardContent, Grid, Skeleton, Stack } from '@mui/material'

export function PageSkeleton() {
  return (
    <Stack spacing={2}>
      <Skeleton variant="text" width="35%" height={40} />
      <Grid container spacing={2}>
        {Array.from({ length: 4 }).map((_, index) => (
          <Grid key={index} size={{ xs: 12, sm: 6, lg: 3 }}>
            <Card variant="outlined">
              <CardContent>
                <Skeleton variant="text" width="50%" />
                <Skeleton variant="text" width="30%" height={44} />
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
      <Skeleton variant="rounded" height={280} />
    </Stack>
  )
}
