import { Outlet, useLocation } from '@tanstack/react-router'
import AccountTreeIcon from '@mui/icons-material/AccountTree'
import AssessmentIcon from '@mui/icons-material/Assessment'
import BugReportIcon from '@mui/icons-material/BugReport'
import DarkModeIcon from '@mui/icons-material/DarkMode'
import FolderZipIcon from '@mui/icons-material/FolderZip'
import HistoryIcon from '@mui/icons-material/History'
import LightModeIcon from '@mui/icons-material/LightMode'
import ListAltIcon from '@mui/icons-material/ListAlt'
import MenuIcon from '@mui/icons-material/Menu'
import RuleIcon from '@mui/icons-material/Rule'
import ViewCompactIcon from '@mui/icons-material/ViewCompact'
import {
  AppBar,
  Box,
  Divider,
  Drawer,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Stack,
  Toolbar,
  Tooltip,
  Typography,
  useMediaQuery,
} from '@mui/material'
import { useTheme } from '@mui/material/styles'
import { useState, type ReactNode } from 'react'

import { useAppDispatch, useAppSelector } from './hooks'
import {
  selectWorkspacePreferences,
  setSidebarCollapsed,
  setThemeMode,
} from '../features/workspace-preferences/workspacePreferencesSlice'
import { BackendHealthChip } from '../features/health/BackendHealthChip'
import { encodeRoutePart } from '../shared/lib/format'
import { navigateInApp } from '../shared/lib/navigation'
import { AppLink } from '../shared/ui/AppLink'

const drawerWidth = 272

type NavItem = {
  href: string
  icon: ReactNode
  label: string
}

function extractRunName(pathname: string) {
  const match = pathname.match(/^\/runs\/([^/]+)/)
  return match ? decodeURIComponent(match[1]) : undefined
}

function navItems(runName: string | undefined): NavItem[] {
  const items: NavItem[] = [
    { href: '/runs', icon: <ListAltIcon fontSize="small" />, label: 'Runs' },
  ]

  if (!runName) return items

  const encodedRunName = encodeRoutePart(runName)
  return [
    ...items,
    { href: `/runs/${encodedRunName}`, icon: <ViewCompactIcon fontSize="small" />, label: 'Overview' },
    { href: `/runs/${encodedRunName}/graph`, icon: <AccountTreeIcon fontSize="small" />, label: 'Graph' },
    { href: `/runs/${encodedRunName}/constraints`, icon: <RuleIcon fontSize="small" />, label: 'Constraints' },
    { href: `/runs/${encodedRunName}/artifacts`, icon: <FolderZipIcon fontSize="small" />, label: 'Artifacts' },
    { href: `/runs/${encodedRunName}/reports`, icon: <AssessmentIcon fontSize="small" />, label: 'Reports' },
    { href: `/runs/${encodedRunName}/test-cases`, icon: <BugReportIcon fontSize="small" />, label: 'Test cases' },
    { href: `/runs/${encodedRunName}/history`, icon: <HistoryIcon fontSize="small" />, label: 'History' },
  ]
}

function isNavItemSelected(pathname: string, href: string) {
  if (href === '/runs') return pathname === href
  return pathname === href || pathname.startsWith(`${href}/`)
}

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const { pathname } = useLocation()
  const runName = extractRunName(pathname)
  const preferences = useAppSelector(selectWorkspacePreferences)
  const dispatch = useAppDispatch()
  const items = navItems(runName)

  return (
    <Stack sx={{ height: '100%' }}>
      <Box sx={{ p: 2 }}>
        <Typography sx={{ fontWeight: 800 }} variant="h3">
          APIPilot
        </Typography>
        <Typography color="text.secondary" variant="caption">
          Artifact query workspace
        </Typography>
      </Box>
      <Divider />
      <List dense sx={{ flex: 1, px: 1 }}>
        {items.map((item) => {
          const selected = isNavItemSelected(pathname, item.href)
          return (
            <ListItemButton
              aria-current={selected ? 'page' : undefined}
              key={item.href}
              onClick={() => {
                navigateInApp(item.href)
                onNavigate?.()
              }}
              selected={selected}
              sx={{ borderRadius: 1, mb: 0.5 }}
            >
              <ListItemIcon sx={{ minWidth: 36 }}>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          )
        })}
      </List>
      <Divider />
      <Stack spacing={1} sx={{ p: 1.5 }}>
        <Tooltip title="Toggle theme mode">
          <IconButton
            aria-label="Toggle theme mode"
            onClick={() => dispatch(setThemeMode(preferences.themeMode === 'dark' ? 'light' : 'dark'))}
          >
            {preferences.themeMode === 'dark' ? <LightModeIcon /> : <DarkModeIcon />}
          </IconButton>
        </Tooltip>
        <Tooltip title="Collapse sidebar">
          <IconButton
            aria-label="Collapse sidebar"
            onClick={() => dispatch(setSidebarCollapsed(!preferences.sidebarCollapsed))}
          >
            <MenuIcon />
          </IconButton>
        </Tooltip>
      </Stack>
    </Stack>
  )
}

export function AppShell() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const theme = useTheme()
  const desktop = useMediaQuery(theme.breakpoints.up('lg'))
  const preferences = useAppSelector(selectWorkspacePreferences)
  const drawerVisible = desktop && !preferences.sidebarCollapsed
  const { pathname } = useLocation()
  const runName = extractRunName(pathname)

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <AppBar
        color="inherit"
        elevation={0}
        position="fixed"
        sx={{
          borderBottom: '1px solid',
          borderColor: 'divider',
          ml: drawerVisible ? `${drawerWidth}px` : 0,
          width: drawerVisible ? `calc(100% - ${drawerWidth}px)` : '100%',
        }}
      >
        <Toolbar variant="dense">
          {!drawerVisible ? (
            <IconButton
              aria-label="Open navigation"
              edge="start"
              onClick={() => setMobileOpen(true)}
              sx={{ mr: 1 }}
            >
              <MenuIcon />
            </IconButton>
          ) : null}
          <Stack direction="row" spacing={1} sx={{ alignItems: 'baseline', minWidth: 0 }}>
            <Typography noWrap sx={{ fontWeight: 700 }}>
              {runName ?? 'Run catalog'}
            </Typography>
            {runName ? (
              <Typography color="text.secondary" noWrap variant="caption">
                query-only local artifact workspace
              </Typography>
            ) : null}
          </Stack>
          <Box sx={{ flex: 1 }} />
          <BackendHealthChip />
          <Box sx={{ width: 12 }} />
          <AppLink href="/runs">Runs</AppLink>
        </Toolbar>
      </AppBar>

      <Drawer
        open={mobileOpen}
        onClose={() => setMobileOpen(false)}
        sx={{ display: { xs: 'block', lg: 'none' } }}
        variant="temporary"
        ModalProps={{ keepMounted: true }}
      >
        <Box sx={{ width: drawerWidth }}>
          <SidebarContent onNavigate={() => setMobileOpen(false)} />
        </Box>
      </Drawer>

      <Drawer
        open
        sx={{
          display: drawerVisible ? 'block' : 'none',
          '& .MuiDrawer-paper': {
            boxSizing: 'border-box',
            width: drawerWidth,
          },
        }}
        variant="permanent"
      >
        <SidebarContent />
      </Drawer>

      <Box
        component="main"
        sx={{
          flex: 1,
          minWidth: 0,
          ml: drawerVisible ? `${drawerWidth}px` : 0,
          p: { xs: 2, md: 3 },
          pt: 8,
        }}
      >
        <Outlet />
      </Box>
    </Box>
  )
}
