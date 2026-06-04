import { Outlet, useLocation, useNavigate } from '@tanstack/react-router'
import AccountTreeIcon from '@mui/icons-material/AccountTree'
import AssessmentIcon from '@mui/icons-material/Assessment'
import BuildIcon from '@mui/icons-material/Build'
import BugReportIcon from '@mui/icons-material/BugReport'
import CompareArrowsIcon from '@mui/icons-material/CompareArrows'
import DarkModeIcon from '@mui/icons-material/DarkMode'
import DashboardIcon from '@mui/icons-material/Dashboard'
import FolderZipIcon from '@mui/icons-material/FolderZip'
import HistoryIcon from '@mui/icons-material/History'
import LightModeIcon from '@mui/icons-material/LightMode'
import ListAltIcon from '@mui/icons-material/ListAlt'
import MenuIcon from '@mui/icons-material/Menu'
import ManageSearchIcon from '@mui/icons-material/ManageSearch'
import PlayCircleIcon from '@mui/icons-material/PlayCircle'
import RuleIcon from '@mui/icons-material/Rule'
import ViewCompactIcon from '@mui/icons-material/ViewCompact'
import {
  AppBar,
  Box,
  Chip,
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
import { lazy, Suspense, useEffect, useState, type ReactNode } from 'react'

import { useAppDispatch, useAppSelector } from './hooks'
import {
  selectWorkspacePreferences,
  setSidebarCollapsed,
  setTableDensity,
  setThemeMode,
} from '../features/workspace-preferences/workspacePreferencesSlice'
import { BackendHealthChip } from '../features/health/BackendHealthChip'
import { ProductTourHost } from '../features/product-tour/ProductTourHost'
import { TourHelpMenu } from '../features/product-tour/TourHelpMenu'
import { TOUR_ANCHORS, tourAnchor } from '../features/product-tour/tourAnchors'
import { encodeRoutePart } from '../shared/lib/format'
import { applySearchParamUpdates, navigateInApp, setNavigationAdapter } from '../shared/lib/navigation'
import { AppLink } from '../shared/ui/AppLink'

const drawerWidthExpanded = 272
const drawerWidthCollapsed = 72

const CommandPalette = lazy(() =>
  import('../features/command-palette/CommandPalette').then((module) => ({ default: module.CommandPalette })),
)

type NavItem = {
  href: string
  icon: ReactNode
  label: string
}

function extractRunName(pathname: string) {
  const match = pathname.match(/^\/runs\/([^/]+)/)
  return match ? decodeURIComponent(match[1]) : undefined
}

function parseNavigationTarget(path: string) {
  const url = new URL(path, window.location.origin)
  return {
    search: Object.fromEntries(url.searchParams.entries()),
    to: url.pathname,
  }
}

function navItems(runName: string | undefined): NavItem[] {
  const items: NavItem[] = [
    { href: '/runs', icon: <ListAltIcon fontSize="small" />, label: 'Runs' },
    { href: '/builder/specs', icon: <BuildIcon fontSize="small" />, label: 'Builder' },
    { href: '/builder/executions', icon: <PlayCircleIcon fontSize="small" />, label: 'Executions' },
    { href: '/compare', icon: <CompareArrowsIcon fontSize="small" />, label: 'Compare' },
  ]

  if (!runName) return items

  const encodedRunName = encodeRoutePart(runName)
  return [
    ...items,
    { href: `/runs/${encodedRunName}`, icon: <ViewCompactIcon fontSize="small" />, label: 'Overview' },
    { href: `/runs/${encodedRunName}/workspace`, icon: <DashboardIcon fontSize="small" />, label: 'Workspace' },
    { href: `/runs/${encodedRunName}/operations`, icon: <ManageSearchIcon fontSize="small" />, label: 'Operations' },
    { href: `/runs/${encodedRunName}/graph`, icon: <AccountTreeIcon fontSize="small" />, label: 'Graph' },
    { href: `/runs/${encodedRunName}/constraints`, icon: <RuleIcon fontSize="small" />, label: 'Constraints' },
    { href: `/runs/${encodedRunName}/artifacts`, icon: <FolderZipIcon fontSize="small" />, label: 'Artifacts' },
    { href: `/runs/${encodedRunName}/reports`, icon: <AssessmentIcon fontSize="small" />, label: 'Reports' },
    { href: `/runs/${encodedRunName}/test-cases`, icon: <BugReportIcon fontSize="small" />, label: 'Test cases' },
    { href: `/runs/${encodedRunName}/history`, icon: <HistoryIcon fontSize="small" />, label: 'History' },
  ]
}

function pageLabel(pathname: string) {
  const segment = pathname.split('/').filter(Boolean).at(-1)
  switch (segment) {
    case 'artifacts':
      return 'Artifacts'
    case 'constraints':
      return 'Constraints'
    case 'graph':
      return 'Graph'
    case 'history':
      return 'History'
    case 'operations':
      return 'Operations'
    case 'reports':
      return 'Reports'
    case 'test-cases':
      return 'Test cases'
    case 'workspace':
      return 'Workspace'
    default:
      return 'Overview'
  }
}

function shellContext(pathname: string, runName: string | undefined) {
  if (pathname.startsWith('/builder/executions')) {
    return {
      mode: 'Builder',
      subtitle: pathname === '/builder/executions' ? 'Builder / Execution Center' : 'Builder / Execution detail',
      title: pathname === '/builder/executions' ? 'Execution Center' : 'Execution detail',
    }
  }

  if (pathname.startsWith('/builder/run-configs')) {
    return {
      mode: 'Builder',
      subtitle: 'Builder / Run Config Builder',
      title: 'Run Config Builder',
    }
  }

  if (pathname.startsWith('/builder/specs')) {
    return {
      mode: 'Builder',
      subtitle: pathname === '/builder/specs' ? 'Builder / Spec Manager' : 'Builder / Spec preview',
      title: pathname === '/builder/specs' ? 'Spec Manager' : 'Spec preview',
    }
  }

  if (pathname.startsWith('/compare')) {
    return {
      mode: 'Compare',
      subtitle: 'Compare / Cross-run evidence lab',
      title: 'Compare Lab',
    }
  }

  if (runName) {
    const label = pageLabel(pathname)
    return {
      mode: 'Investigation',
      subtitle: `Investigation / ${label}`,
      title: runName,
    }
  }

  return {
    mode: 'Catalog',
    subtitle: 'Local artifacts and generated runs',
    title: 'Run catalog',
  }
}

function isNavItemSelected(pathname: string, href: string) {
  if (href === '/runs') return pathname === href
  if (href === '/builder/specs') return pathname.startsWith('/builder') && !pathname.startsWith('/builder/executions')
  if (href === '/builder/executions') return pathname.startsWith('/builder/executions')
  return pathname === href || pathname.startsWith(`${href}/`)
}

function SidebarContent({
  collapsed = false,
  onNavigate,
  showCollapseControl = true,
}: {
  collapsed?: boolean
  onNavigate?: () => void
  showCollapseControl?: boolean
}) {
  const { pathname } = useLocation()
  const runName = extractRunName(pathname)
  const preferences = useAppSelector(selectWorkspacePreferences)
  const dispatch = useAppDispatch()
  const items = navItems(runName)

  return (
    <Stack sx={{ height: '100%' }}>
      <Box
        sx={{
          display: 'flex',
          justifyContent: collapsed ? 'center' : 'flex-start',
          minHeight: collapsed ? 64 : 'auto',
          p: collapsed ? 1.25 : 2,
        }}
        {...tourAnchor(TOUR_ANCHORS.appSidebar)}
      >
        {collapsed ? (
          <Box
            aria-label="APIPilot artifact workspace"
            sx={(theme) => ({
              alignItems: 'center',
              bgcolor: theme.apiTesting.httpMethod.GET.bg,
              border: '1px solid',
              borderColor: theme.apiTesting.httpMethod.GET.border,
              borderRadius: 1.25,
              color: theme.apiTesting.httpMethod.GET.fg,
              display: 'flex',
              fontWeight: 900,
              height: 40,
              justifyContent: 'center',
              width: 40,
            })}
          >
            AP
          </Box>
        ) : (
          <Box sx={{ minWidth: 0 }}>
            <Typography sx={{ fontWeight: 800 }} variant="h3">
              APIPilot
            </Typography>
            <Typography color="text.secondary" variant="caption">
              Artifact Command Center
            </Typography>
          </Box>
        )}
      </Box>
      <Divider />
      <List dense sx={{ flex: 1, px: 1 }}>
        {items.map((item) => {
          const selected = isNavItemSelected(pathname, item.href)
          return (
            <Tooltip key={item.href} placement="right" title={collapsed ? item.label : ''}>
              <ListItemButton
                aria-current={selected ? 'page' : undefined}
                onClick={() => {
                  navigateInApp(item.href)
                  onNavigate?.()
                }}
                selected={selected}
                sx={{
                  borderRadius: 1,
                  justifyContent: collapsed ? 'center' : 'flex-start',
                  mb: 0.5,
                  minHeight: 42,
                  px: collapsed ? 1 : 1.25,
                }}
              >
                <ListItemIcon
                  sx={{
                    color: 'inherit',
                    justifyContent: 'center',
                    minWidth: collapsed ? 0 : 36,
                  }}
                >
                  {item.icon}
                </ListItemIcon>
                {collapsed ? null : (
                  <ListItemText
                    primary={item.label}
                    slotProps={{ primary: { noWrap: true, variant: 'body2' } }}
                  />
                )}
              </ListItemButton>
            </Tooltip>
          )
        })}
      </List>
      {showCollapseControl ? (
        <>
          <Divider />
          <Stack
            direction={collapsed ? 'column' : 'row'}
            spacing={1}
            sx={{
              justifyContent: collapsed ? 'center' : 'space-between',
              p: 1.5,
            }}
          >
            {!collapsed ? (
              <Typography color="text.secondary" variant="caption">
                Workspace
              </Typography>
            ) : null}
            <Tooltip title={preferences.sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}>
              <IconButton
                aria-label={preferences.sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
                onClick={() => dispatch(setSidebarCollapsed(!preferences.sidebarCollapsed))}
              >
                <MenuIcon />
              </IconButton>
            </Tooltip>
          </Stack>
        </>
      ) : null}
    </Stack>
  )
}

export function AppShell() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const theme = useTheme()
  const desktop = useMediaQuery(theme.breakpoints.up('lg'))
  const preferences = useAppSelector(selectWorkspacePreferences)
  const dispatch = useAppDispatch()
  const location = useLocation()
  const navigate = useNavigate()
  const drawerWidth = desktop
    ? preferences.sidebarCollapsed
      ? drawerWidthCollapsed
      : drawerWidthExpanded
    : 0
  const { pathname } = location
  const runName = extractRunName(pathname)
  const context = shellContext(pathname, runName)
  const densityLabel = preferences.tableDensity === 'compact' ? 'Compact density' : 'Comfortable density'

  useEffect(() => {
    setNavigationAdapter({
      navigateInApp: (path) => {
        const target = parseNavigationTarget(path)
        void navigate({ search: target.search as never, to: target.to as never })
      },
      replaceSearchParams: (updates) => {
        void navigate({
          replace: true,
          search: (currentSearch) =>
            applySearchParamUpdates(currentSearch as Record<string, unknown>, updates) as never,
        })
      },
    })
  }, [navigate])

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <AppBar
        color="inherit"
        elevation={0}
        position="fixed"
        sx={{
          backgroundImage: theme.apiTesting.gradient.topBar,
          borderBottom: '1px solid',
          borderColor: theme.apiTesting.border.default,
          backdropFilter: 'blur(16px)',
          ml: drawerWidth ? `${drawerWidth}px` : 0,
          width: drawerWidth ? `calc(100% - ${drawerWidth}px)` : '100%',
        }}
      >
        <Toolbar variant="dense">
          {!desktop ? (
            <IconButton
              aria-label="Open navigation"
              edge="start"
              onClick={() => setMobileOpen(true)}
              sx={{ mr: 1 }}
            >
              <MenuIcon />
            </IconButton>
          ) : null}
          <Stack direction="row" spacing={1} sx={{ alignItems: 'center', minWidth: 0 }}>
            <Stack
              direction="row"
              spacing={1}
              sx={{ alignItems: 'center', minWidth: 0 }}
              {...tourAnchor(TOUR_ANCHORS.appRunContext)}
            >
              <Chip label={context.mode} size="small" variant="outlined" />
              <Typography noWrap sx={{ fontWeight: 700, minWidth: 0 }}>
                {context.title}
              </Typography>
              <Typography color="text.secondary" noWrap variant="caption">
                {context.subtitle}
              </Typography>
            </Stack>
          </Stack>
          <Box sx={{ flex: 1 }} />
          <Box {...tourAnchor(TOUR_ANCHORS.appDensityControl)}>
            <Tooltip title={densityLabel}>
              <IconButton
                aria-label="Toggle table density"
                onClick={() =>
                  dispatch(
                    setTableDensity(preferences.tableDensity === 'compact' ? 'comfortable' : 'compact'),
                  )
                }
                size="small"
              >
                <ViewCompactIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </Box>
          <Tooltip title="Toggle theme mode">
            <IconButton
              aria-label="Toggle theme mode"
              onClick={() => dispatch(setThemeMode(preferences.themeMode === 'dark' ? 'light' : 'dark'))}
              size="small"
            >
              {preferences.themeMode === 'dark' ? <LightModeIcon fontSize="small" /> : <DarkModeIcon fontSize="small" />}
            </IconButton>
          </Tooltip>
          <Box {...tourAnchor(TOUR_ANCHORS.appBackendHealth)}>
            <BackendHealthChip />
          </Box>
          <Suspense fallback={null}>
            <CommandPalette runName={runName} />
          </Suspense>
          <TourHelpMenu pathname={pathname} />
          <Box sx={{ width: 12 }} />
          <AppLink href="/runs">Catalog</AppLink>
        </Toolbar>
      </AppBar>

      <Drawer
        open={mobileOpen}
        onClose={() => setMobileOpen(false)}
        sx={{ display: { xs: 'block', lg: 'none' } }}
        variant="temporary"
        ModalProps={{ keepMounted: true }}
      >
        <Box sx={{ width: drawerWidthExpanded }}>
          <SidebarContent onNavigate={() => setMobileOpen(false)} showCollapseControl={false} />
        </Box>
      </Drawer>

      <Drawer
        open
        sx={{
          display: { xs: 'none', lg: 'block' },
          '& .MuiDrawer-paper': {
            boxSizing: 'border-box',
            width: drawerWidth,
          },
        }}
        variant="permanent"
      >
        <SidebarContent collapsed={preferences.sidebarCollapsed} />
      </Drawer>

      <Box
        component="main"
        sx={{
          flex: 1,
          minWidth: 0,
          ml: drawerWidth ? `${drawerWidth}px` : 0,
          p: { xs: 2, md: 3 },
          pt: { xs: '64px', md: '72px' },
        }}
      >
        <Outlet />
      </Box>
      <ProductTourHost />
    </Box>
  )
}
