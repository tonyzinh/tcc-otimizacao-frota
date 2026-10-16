import { describe, expect, it } from 'vitest'
import { resolveAlgorithm } from './ExperimentContext'
import { distanceLabel } from './labels'

describe('resolveAlgorithm', () => {
  const real = ['baseline', 'guloso', 'proporcional', 'regra_limiar'] as const

  it('mantém a escolha quando o experimento tem o algoritmo', () => {
    expect(resolveAlgorithm(real, 'proporcional')).toBe('proporcional')
  })

  it('troca um algoritmo ausente pelo primeiro proposto disponível', () => {
    expect(resolveAlgorithm(real, 'atribuicao_otima')).toBe('guloso')
  })

  it('evita repetir a estratégia do outro lado da comparação', () => {
    expect(resolveAlgorithm(real, 'atribuicao_otima', 'guloso')).toBe('proporcional')
    expect(resolveAlgorithm(real, 'guloso', 'guloso')).toBe('proporcional')
  })
})

describe('distanceLabel', () => {
  it('declara o fator rua/reta quando usado', () => {
    expect(distanceLabel('haversine')).toBe('Haversine')
    expect(distanceLabel('haversine_fator_rua')).toBe('Haversine × fator rua/reta')
  })
})
