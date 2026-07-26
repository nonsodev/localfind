# Contributing to LocalFind

Thank you for your interest in contributing to LocalFind! This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/nonsodev/localfind.git`
3. Create a branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Test your changes
6. Commit: `git commit -m "Add: your feature description"`
7. Push: `git push origin feature/your-feature-name`
8. Open a Pull Request

## Development Setup

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Code Style

### Python
- Follow PEP 8
- Use type hints where possible
- Add docstrings to functions
- Keep functions focused and small

### JavaScript/React
- Use functional components with hooks
- Follow React best practices
- Use meaningful variable names
- Add comments for complex logic

## Testing

Before submitting a PR:
- [ ] Test backend endpoints
- [ ] Test frontend UI
- [ ] Test with different file types
- [ ] Check for console errors
- [ ] Verify documentation is updated

## Areas for Contribution

### High Priority
- Additional file format support (e.g., EPUB, HTML)
- Performance optimizations
- Test coverage
- Error handling improvements

### Medium Priority
- UI/UX enhancements
- Additional language support
- Documentation improvements
- Example datasets

### Low Priority
- Mobile responsiveness
- Keyboard shortcuts
- Themes/customization
- Export features

## Pull Request Guidelines

1. **Title**: Clear, descriptive title
2. **Description**: Explain what and why
3. **Testing**: Describe how you tested
4. **Screenshots**: For UI changes
5. **Documentation**: Update relevant docs

## Reporting Issues

When reporting issues, include:
- Operating system
- Python version
- Node.js version
- Steps to reproduce
- Expected vs actual behavior
- Error messages/logs
- Screenshots (if applicable)

## Questions?

Open an issue with the "question" label or start a discussion.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
