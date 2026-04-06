from src.features.build import build_features_base


# IsAutoPayment é 0 para "Electronic check" e 1 para "Bank transfer (automatic)"
def test_auto_payment(sample_raw_data):
    df = build_features_base(sample_raw_data)
    assert df.loc[0, "IsAutoPayment"] == 0, f'Esperado 0 para IsAutoPayment do cliente 1, mas obteve {df.loc[0, "IsAutoPayment"]}'
    assert df.loc[1, "IsAutoPayment"] == 1, f'Esperado 1 para IsAutoPayment do cliente 2, mas obteve {df.loc[1, "IsAutoPayment"]}'

# Contract do cliente 1 é 0 (Month-to-month)
def test_contract_cliente_1(sample_raw_data):
    df = build_features_base(sample_raw_data)
    assert df.loc[0, "Contract"] == 0, f'Esperado 0 para Contract do cliente 1, mas obteve {df.loc[0, "Contract"]}'

# PaymentMethod não existe mais no DataFrame após o processamento
def test_payment_method_removido(sample_raw_data):
    df = build_features_base(sample_raw_data)
    assert "PaymentMethod" not in df.columns, 'Teste falhou: PaymentMethod ainda existe no DataFrame após o processamento.'

# ServicesBundle do cliente 1 é a soma correta dos seus 6 serviços
def test_services_bundle_cliente_1(sample_raw_data):
    df = build_features_base(sample_raw_data)
    expected_bundle = 2 
    assert df.loc[0, "ServicesBundle"] == expected_bundle, f'Esperado {expected_bundle} para ServicesBundle do cliente 1, mas obteve {df.loc[0, "ServicesBundle"]}'