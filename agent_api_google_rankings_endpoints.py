"""
Google Rankings API Endpoints
Aceste endpoint-uri trebuie adăugate în agent_api.py
"""

# Add after the learning endpoints (around line 5000)

# ------------- GOOGLE RANKINGS & SLAVE AGENTS ENDPOINTS -------------

@app.get("/api/agents/{agent_id}/google-rankings-map")
async def api_get_google_rankings_map(agent_id: str):
    """
    Returnează harta completă de rankings Google pentru un agent
    Folosit de GoogleRankingsMap.jsx component
    """
    try:
        from bson import ObjectId
        
        # Get all rankings for this agent
        rankings = list(db.google_rankings.find(
            {'agent_id': agent_id},
            sort=[('checked_at', -1)]
        ))
        
        if not rankings:
            return {
                'agent_id': agent_id,
                'exists': False,
                'total_keywords': 0,
                'rankings': [],
                'message': 'No rankings data. Run SERP discovery first.'
            }
        
        # Format rankings for frontend
        map_data = []
        for ranking in rankings:
            ranking['_id'] = str(ranking['_id'])
            if 'checked_at' in ranking:
                ranking['checked_at'] = ranking['checked_at'].isoformat()
            
            map_data.append({
                'keyword': ranking['keyword'],
                'master_position': ranking.get('master_position'),
                'serp_results': ranking.get('serp_results', []),
                'slave_ids': ranking.get('slave_ids', []),
                'checked_at': ranking.get('checked_at'),
                'in_top_10': ranking.get('master_position') is not None and ranking['master_position'] <= 10,
                'in_top_20': ranking.get('master_position') is not None and ranking['master_position'] <= 20
            })
        
        # Statistics
        in_top_3 = sum(1 for r in map_data if r.get('master_position') and r['master_position'] <= 3)
        in_top_10 = sum(1 for r in map_data if r.get('master_position') and r['master_position'] <= 10)
        in_top_20 = sum(1 for r in map_data if r.get('master_position') and r['master_position'] <= 20)
        missing = sum(1 for r in map_data if r.get('master_position') is None)
        
        return {
            'agent_id': agent_id,
            'exists': True,
            'total_keywords': len(map_data),
            'rankings': map_data,
            'statistics': {
                'in_top_3': in_top_3,
                'in_top_10': in_top_10,
                'in_top_20': in_top_20,
                'missing': missing
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting rankings map: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agents/{agent_id}/google-ads-strategy")
async def api_get_google_ads_strategy(agent_id: str):
    """
    Returnează strategia Google Ads generată de DeepSeek
    """
    try:
        from bson import ObjectId
        
        # Get latest strategy
        strategy = db.competitive_strategies.find_one(
            {'agent_id': agent_id},
            sort=[('generated_at', -1)]
        )
        
        if not strategy:
            return {
                'agent_id': agent_id,
                'exists': False,
                'message': 'No Google Ads strategy generated yet. Run SERP discovery with slaves first.'
            }
        
        # Format for frontend
        strategy['_id'] = str(strategy['_id'])
        if 'generated_at' in strategy:
            strategy['generated_at'] = strategy['generated_at'].isoformat()
        
        return {
            'agent_id': agent_id,
            'exists': True,
            'strategy': strategy
        }
        
    except Exception as e:
        logger.error(f"Error getting Google Ads strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agents/{agent_id}/slave-agents")
async def api_get_slave_agents(agent_id: str, limit: int = 100):
    """
    Returnează toți agenții slave pentru un master agent
    """
    try:
        slaves = list(db.site_agents.find(
            {
                'master_ids': agent_id,
                'type': 'slave'
            },
            limit=limit,
            sort=[('created_at', -1)]
        ))
        
        # Format slaves
        for slave in slaves:
            slave['_id'] = str(slave['_id'])
            if 'created_at' in slave:
                slave['created_at'] = slave['created_at'].isoformat()
            if 'updated_at' in slave:
                slave['updated_at'] = slave['updated_at'].isoformat()
        
        return {
            'agent_id': agent_id,
            'total_slaves': len(slaves),
            'slaves': slaves
        }
        
    except Exception as e:
        logger.error(f"Error getting slave agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/workflows/start-serp-discovery-with-slaves")
async def api_start_serp_discovery_with_slaves(
    background_tasks: BackgroundTasks,
    agent_id: str = Body(...),
    num_keywords: Optional[int] = Body(None)
):
    """
    Pornește workflow-ul complet de SERP discovery + slave creation + strategy
    """
    try:
        from workflow_manager import start_serp_discovery_with_slaves
        
        # Start workflow
        workflow_id = await start_serp_discovery_with_slaves(
            agent_id=agent_id,
            num_keywords=num_keywords
        )
        
        return {
            'workflow_id': workflow_id,
            'status': 'started',
            'agent_id': agent_id,
            'num_keywords': num_keywords or 'all',
            'message': f'SERP discovery with slave creation started'
        }
        
    except Exception as e:
        logger.error(f"Error starting SERP discovery with slaves: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agents/{agent_id}/rankings-summary")
async def api_get_rankings_summary(agent_id: str):
    """
    Returnează un summary rapid al rankings pentru dashboard
    """
    try:
        rankings = list(db.google_rankings.find({'agent_id': agent_id}))
        
        if not rankings:
            return {
                'agent_id': agent_id,
                'has_data': False,
                'total_keywords': 0
            }
        
        # Calculate summary
        positions = [r.get('master_position') for r in rankings if r.get('master_position')]
        
        summary = {
            'agent_id': agent_id,
            'has_data': True,
            'total_keywords': len(rankings),
            'tracked_keywords': len(positions),
            'missing_keywords': len(rankings) - len(positions),
            'best_position': min(positions) if positions else None,
            'worst_position': max(positions) if positions else None,
            'avg_position': round(sum(positions) / len(positions), 1) if positions else None,
            'in_top_10': sum(1 for p in positions if p <= 10),
            'in_top_20': sum(1 for p in positions if p <= 20),
            'last_checked': max(
                r.get('checked_at')
                for r in rankings
                if r.get('checked_at')
            ).isoformat() if rankings else None
        }
        
        return summary
        
    except Exception as e:
        logger.error(f"Error getting rankings summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

