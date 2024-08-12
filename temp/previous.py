# cur.execute("SELECT embedding FROM users WHERE id = %s", (target_user_id,))
#             target_embedding = cur.fetchone()
            
#             if target_embedding is None or target_embedding[0] is None:
#                 print(f"User {target_user_id} does not have an embedding.")
#                 return []
            
#             cur.execute("""
#                 SELECT id, username, 1 - (embedding <=> (SELECT embedding FROM users WHERE id = %s)) AS similarity
#                 FROM users
#                 WHERE id != %s
#                 ORDER BY embedding <=> (SELECT embedding FROM users WHERE id = %s)
#                 LIMIT %s
#             """, (target_user_id, target_user_id, target_user_id, limit))
