SELECT Category, AI_Adoption, AI_Adoption_grade
FROM ai_adoption
WHERE "Group" = 'Industry' AND AI_Adoption IS NOT NULL
ORDER BY AI_Adoption DESC
LIMIT 5;

SELECT "Group", ROUND(AVG(AI_Adoption), 1) AS avg_adoption,
       ROUND(MAX(AI_Adoption) - MIN(AI_Adoption), 1) AS spread
FROM ai_adoption
WHERE Is_Total = 0 AND AI_Adoption IS NOT NULL
GROUP BY "Group"
ORDER BY spread DESC;