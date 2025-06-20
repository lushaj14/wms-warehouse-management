# Test Documentation

## Test Yapısı

```
tests/
├── unit/                 # Unit testler
│   ├── test_dao.py      # DAO katmanı testleri
│   ├── test_settings.py # Settings modül testleri
│   └── test_constants.py # Constants testleri
├── integration/         # Integration testler
│   └── test_backorder_integration.py
├── fixtures/           # Test verileri
├── conftest.py        # Pytest fixtures
├── utils.py           # Test yardımcıları
└── README.md          # Bu dosya
```

## Test Çalıştırma

### Tüm Testler
```bash
python -m pytest
# veya
make test
```

### Sadece Unit Testler
```bash
python -m pytest tests/unit/
# veya
make test-unit
```

### Sadece Integration Testler
```bash
python -m pytest tests/integration/
# veya
make test-integration
```

### Coverage ile
```bash
python -m pytest --cov=app --cov-report=html
# veya
make test-coverage
```

### Belirli Test Kategorileri
```bash
# Sadece hızlı testler
python -m pytest -m "not slow"

# Sadece veritabanı testleri
python -m pytest -m database

# Sadece UI testleri
python -m pytest -m ui
```

## Test Yazma Kuralları

### 1. Test Dosya İsimlendirme
- Unit testler: `test_[module_name].py`
- Integration testler: `test_[feature]_integration.py`

### 2. Test Fonksiyon İsimlendirme
```python
def test_[what_it_tests]_[expected_outcome]():
    """Açıklayıcı docstring"""
    pass
```

### 3. Test Yapısı (AAA Pattern)
```python
def test_function_with_valid_input_returns_expected_result():
    """Test fonksiyonun geçerli input ile doğru sonuç döndürmesi"""
    # Arrange
    input_data = "test_input"
    expected_result = "expected_output"
    
    # Act
    result = function_under_test(input_data)
    
    # Assert
    assert result == expected_result
```

### 4. Mock Kullanımı
```python
@patch('app.dao.logo.get_conn')
def test_database_operation(mock_conn):
    """Database operasyonu mock testi"""
    # Mock setup
    mock_conn.return_value.__enter__.return_value.execute.return_value = Mock()
    
    # Test code
    result = function_that_uses_db()
    
    # Assertions
    assert mock_conn.called
```

### 5. Fixture Kullanımı
```python
def test_with_sample_data(sample_order_data):
    """Fixture ile test"""
    order = sample_order_data
    assert order["order_no"] == "TEST001"
```

## Test Kategorileri

### Markers
- `@pytest.mark.unit` - Unit testler
- `@pytest.mark.integration` - Integration testler
- `@pytest.mark.slow` - Yavaş testler
- `@pytest.mark.database` - Veritabanı gerektiren testler
- `@pytest.mark.ui` - GUI testleri

### Kullanım
```python
@pytest.mark.unit
@pytest.mark.database
def test_database_function():
    pass
```

## Test Verileri

### Factory Pattern
```python
from tests.conftest import TestDataFactory

def test_with_factory_data():
    order = TestDataFactory.create_order(order_no="CUSTOM001")
    line = TestDataFactory.create_order_line(qty_ordered=100)
```

### Fixtures
```python
def test_with_fixture(sample_order_data, mock_db_connection):
    # Test implementation
    pass
```

## Coverage Hedefleri

- **Minimum Coverage**: %70
- **Unit Tests**: %90+
- **Integration Tests**: %60+

## Best Practices

1. **Her fonksiyon için test yaz**
2. **Happy path ve error case'leri test et**
3. **Mock'ları doğru kullan**
4. **Test'ler birbirinden bağımsız olmalı**
5. **Test isimleri açıklayıcı olmalı**
6. **Arrange-Act-Assert pattern'ı kullan**
7. **Test verilerini fixture'larda topla**

## Troubleshooting

### Sık Karşılaşılan Sorunlar

1. **Import Error**
```bash
# Çözüm: PYTHONPATH ayarla
export PYTHONPATH="${PYTHONPATH}:."
```

2. **Database Connection Error**
```bash
# Test environment variables kontrol et
pytest -v -s tests/unit/test_dao.py::test_connection
```

3. **Mock Not Working**
```python
# Doğru import path kullan
@patch('app.module.function')  # import edilen yerdeki path
```