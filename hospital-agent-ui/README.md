# Hospital Agent React UI

A modern React + TypeScript application for hospital resource management and AI-powered multi-agent coordination.

## 🚀 Quick Start

```bash
# Install dependencies (if not done)
npm install

# Start development server
npm run dev

# Open http://localhost:5173
```

## 📦 What's Included

### ✅ Complete Setup
- React 19 + TypeScript
- Vite build tool
- React Router v6 for navigation
- Responsive design with modern CSS

### ✅ Completed Pages
1. **Home** (`/`) - Navigation hub with 8 dashboard cards
2. **Dashboard** (`/dashboard`) - Complete example with stats, agents, alerts, activity

### 🔨 To Complete
Create 6 remaining pages (see `REACT_SETUP_GUIDE.md` for details):
- Parliament - AI negotiation interface
- Chat - AI assistant
- Predictions - Analytics dashboard
- Resources - Inventory management
- Alerts - Notification system
- History - Activity timeline
- Documents - Protocol library

## 📁 Project Structure

```
src/
├── pages/
│   ├── Home.tsx + Home.css ✅
│   ├── Dashboard.tsx + Dashboard.css ✅
│   └── [6 more pages to create]
├── App.tsx (routing)
├── main.tsx (entry)
└── index.css (global styles)
```

## 🎯 Development Workflow

### 1. Create Component Files
```bash
touch src/pages/Parliament.tsx
touch src/pages/Parliament.css
```

### 2. Convert HTML to React
- Change `class=` to `className=`
- Change inline styles to React format
- Replace `<a>` with `<Link>`
- Import CSS file

### 3. Add Route
```typescript
// In App.tsx
import Parliament from './pages/Parliament';

<Route path="/parliament" element={<Parliament />} />
```

### 4. Test
```bash
npm run dev
# Navigate to http://localhost:5173/parliament
```

## 📚 Reference Documents

- **`REACT_SETUP_GUIDE.md`** - Comprehensive step-by-step guide
- **`UI_DASHBOARD_REQUIREMENTS.md`** - Original specifications
- **`hospital_agent/ui_mocks/`** - HTML mockups to convert

## 🛠️ Available Scripts

```bash
npm run dev      # Start dev server
npm run build    # Build for production
npm run preview  # Preview production build
npm run lint     # Run ESLint
```

## 🔗 Reference Example

The **Dashboard** component is a complete working example showing:
- Proper TypeScript typing
- React Router Link usage
- CSS module structure
- Component organization
- Dummy data patterns

Use it as a template for creating other pages.

## 📋 Conversion Checklist

For each new page:
- [ ] Create `.tsx` and `.css` files
- [ ] Import React Router Link
- [ ] Convert HTML classes to className
- [ ] Add route to App.tsx
- [ ] Test navigation works
- [ ] Verify styling matches mockup

## 🎨 Design System

**Colors:**
- Primary: `#3B82F6` (Blue)
- Success: `#10B981` (Green)
- Warning: `#F59E0B` (Orange)
- Danger: `#EF4444` (Red)
- Gray: `#6B7280`

**Spacing:**
- Section gaps: `24px`
- Card padding: `20-24px`
- Element gaps: `12-16px`

**Components:**
- Cards: White background, `border-radius: 12px`, subtle shadow
- Buttons: `border-radius: 8px`, hover effects
- Headers: `32px` font size

## 🔮 Future Enhancements

1. **API Integration** - Connect to FastAPI backend
2. **State Management** - Add Redux or Zustand
3. **Charts** - Integrate Chart.js or Recharts
4. **Real-time** - WebSocket for live updates
5. **Forms** - Add validation with React Hook Form
6. **Tests** - Unit and integration tests

## 🐛 Troubleshooting

**Port already in use?**
```bash
# Kill process on port 5173
lsof -ti:5173 | xargs kill -9
```

**Module not found?**
```bash
npm install
```

**Styles not applying?**
- Check CSS import in component
- Verify className (not class)
- Clear browser cache

## 📞 Support

- Check `REACT_SETUP_GUIDE.md` for detailed instructions
- Review Dashboard.tsx as reference
- Compare with HTML mockups in `ui_mocks/`

## 🏆 Success Checklist

- [x] React app created with Vite
- [x] Dependencies installed
- [x] Home page complete
- [x] Dashboard example complete
- [x] Routing configured
- [ ] 6 remaining pages created
- [ ] All navigation working
- [ ] API integration ready

---

Built with ❤️ for Hospital Agent v2.0.0
